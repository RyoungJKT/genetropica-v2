#!/usr/bin/env python3
"""Generate colab/ns5_enrichment_validation.ipynb (a self-contained Colab notebook
that re-validates DENV NS5 docking against a property-matched, DUD-E-style decoy set).
Run: python3 colab/_build_nb.py"""
import json
from pathlib import Path

CELLS = []
def md(src): CELLS.append(("markdown", src))
def code(src): CELLS.append(("code", src))

md("""# GeneTropica - NS5 retrospective enrichment (property-matched decoys)

Re-validates the dengue **NS5** docking on a **standard, property-matched (DUD-E-style) decoy set**, the rigorous version of the project's original benchmark. It uses the same receptor (`5CCV_clean.pdbqt`) and grid box as the original screen, so the result is directly comparable.

**What it does:** loads the 8 known NS5 inhibitors, pulls a drug-like pool from ChEMBL, picks decoys matched to each active on size/logP/H-bonding/charge but topologically dissimilar (true decoys, not analogues), docks everything with AutoDock Vina, and reports ROC-AUC + enrichment factors.

**Runtime:** AutoDock Vina runs on CPU (no GPU needed), ~1-3 h for ~200 ligands. Docking is **checkpointed/resumable**, so a Colab disconnect won't lose progress, just re-run the docking cell. Then it downloads a results JSON to send back for dashboard integration.

Run via **Runtime > Run all**.""")

code("""# Setup (~2 min): RDKit, OpenBabel, AutoDock Vina binary (CPU), scikit-learn.
!pip -q install rdkit scikit-learn requests tqdm >/dev/null 2>&1
!apt-get -qq install -y openbabel >/dev/null 2>&1
import os, subprocess, json, requests
if not os.path.exists('vina'):
    url = 'https://github.com/ccsb-scripps/AutoDock-Vina/releases/download/v1.2.5/vina_1.2.5_linux_x86_64'
    open('vina', 'wb').write(requests.get(url, timeout=180).content)
    os.chmod('vina', 0o755)
print('vina:', subprocess.run(['./vina', '--version'], capture_output=True, text=True).stdout.strip())""")

md("## Parameters")
code("""RAW = 'https://raw.githubusercontent.com/RyoungJKT/genetropica-v2/main'
RECEPTOR_URL      = RAW + '/colab/5CCV_clean.pdbqt'   # the project's exact NS5 receptor
GRID_CENTER       = [-118.9, 60.8, 40.2]              # methods.json (DENV_NS5)
BOX               = 25
EXHAUSTIVENESS    = 8        # matches the original screen; lower (e.g. 4) to go faster
DECOYS_PER_ACTIVE = 25       # DUD-E uses 50; 25 keeps free-Colab runtime sane
DECOY_POOL_SIZE   = 4000     # drug-like molecules pulled from ChEMBL to match against
os.makedirs('lig', exist_ok=True)""")

md("## 1. The 8 known DENV NS5 / RdRp inhibitors (the actives)")
code("""# Nucleoside analogues + prodrugs with reported anti-NS5 activity (the original validation set).
ACTIVES = {
 '2_c_methyladenosine': 'C[C@@]1(O)[C@H](CO)O[C@@H](n2cnc3c(N)ncnc32)[C@@H]1O',
 '7_deaza_2_c_methyladenosine': 'C[C@@]1(O)[C@H](CO)O[C@@H](n2ccc3c(N)ncnc32)[C@@H]1O',
 'balapiravir': 'CCOC(=O)[C@@H](C)N[P@@](=O)(OC[C@H]1O[C@@H](n2ccc(=O)[nH]c2=O)[C@@](C)(O)[C@@H]1O)Oc1ccccc1',
 'galidesivir': 'Nc1ncnc2c1ncn2[C@@H]1C[C@@H](O)[C@H](CO)N1',
 'gs_461203': 'CC(C)C(=O)O[P@@](=O)(O)O[P@@](=O)(O)OC[C@H]1O[C@@H](n2cc(F)c(N)nc2=O)[C@H](O)[C@@H]1O',
 'nitd008': 'Nc1ncnc2c1ncn2[C@H]1C=C(CO)[C@H](CO)O1',
 'ribavirin': 'NC(=O)c1ncnn1[C@@H]1O[C@@H](CO)[C@H](O)[C@@H]1O',
 'sofosbuvir': 'CC(C)OC(=O)[C@@H](C)N[P@](=O)(OC[C@H]1O[C@@H](n2ccc(=O)[nH]c2=O)[C@H](C(F)(F)F)[C@@H]1O)Oc1ccccc1',
}
print(len(ACTIVES), 'actives')""")

md("## 2. Drug-like pool from ChEMBL (to draw decoys from)")
code("""from rdkit import Chem, RDLogger
RDLogger.DisableLog('rdApp.*')
pool, offset = [], 0
while len(pool) < DECOY_POOL_SIZE:
    u = ('https://www.ebi.ac.uk/chembl/api/data/molecule.json'
         '?molecule_properties__full_mwt__gte=250&molecule_properties__full_mwt__lte=600'
         f'&limit=1000&offset={offset}')
    mols = requests.get(u, timeout=90).json().get('molecules', [])
    if not mols:
        break
    for m in mols:
        s = (m.get('molecule_structures') or {}).get('canonical_smiles')
        if s and '.' not in s:
            pool.append(s)
    offset += 1000
print('pool SMILES:', len(pool))""")

md("## 3. Property-matched, topologically-dissimilar decoys (DUD-E logic)")
code("""from rdkit.Chem import Descriptors, rdMolDescriptors, AllChem, DataStructs
def feats(m):
    return dict(mw=Descriptors.MolWt(m), logp=Descriptors.MolLogP(m),
                hbd=rdMolDescriptors.CalcNumHBD(m), hba=rdMolDescriptors.CalcNumHBA(m),
                rot=rdMolDescriptors.CalcNumRotatableBonds(m), q=Chem.GetFormalCharge(m),
                fp=AllChem.GetMorganFingerprintAsBitVect(m, 2, 2048))
act = {n: feats(Chem.MolFromSmiles(s)) for n, s in ACTIVES.items()}
act_fps = [a['fp'] for a in act.values()]
poolf = []
for s in pool:
    mm = Chem.MolFromSmiles(s)
    if mm is not None:
        poolf.append((s, feats(mm)))

def matches(a, p):
    return (abs(a['mw'] - p['mw']) <= 25 and abs(a['logp'] - p['logp']) <= 1.0
            and abs(a['hbd'] - p['hbd']) <= 1 and abs(a['hba'] - p['hba']) <= 2
            and abs(a['rot'] - p['rot']) <= 2 and a['q'] == p['q'])

used, decoys = set(), {}
for n, a in act.items():
    picked = []
    for i, (s, p) in enumerate(poolf):
        if i in used or not matches(a, p):
            continue
        if max(DataStructs.BulkTanimotoSimilarity(p['fp'], act_fps)) >= 0.35:
            continue  # too similar to a real active -> not a decoy
        picked.append(i)
        if len(picked) >= DECOYS_PER_ACTIVE:
            break
    used.update(picked)
    for j, i in enumerate(picked):
        decoys[f'decoy_{n}_{j:02d}'] = poolf[i][0]
print('property-matched decoys:', len(decoys))
if len(decoys) < 5 * len(ACTIVES):
    print('NOTE: few decoys found - consider raising DECOY_POOL_SIZE or loosening tolerances.')""")

md("## 4. 3D prep (RDKit embed -> pdbqt via OpenBabel)")
code("""def prep(name, smiles):
    m = Chem.MolFromSmiles(smiles)
    if m is None:
        return None
    m = Chem.AddHs(m)
    if AllChem.EmbedMolecule(m, AllChem.ETKDGv3()) != 0:
        return None
    try:
        AllChem.MMFFOptimizeMolecule(m)
    except Exception:
        pass
    sdf = f'lig/{name}.sdf'
    Chem.MolToMolFile(m, sdf)
    pq = f'lig/{name}.pdbqt'
    subprocess.run(['obabel', sdf, '-O', pq, '--partialcharge', 'gasteiger'], capture_output=True)
    return pq if os.path.exists(pq) and os.path.getsize(pq) > 0 else None

from tqdm.auto import tqdm
ligs = {}
for n, s in tqdm({**ACTIVES, **decoys}.items(), desc='prep'):
    pq = prep(n, s)
    if pq:
        ligs[n] = (pq, 1 if n in ACTIVES else 0)
print('prepared:', len(ligs), '|', sum(v[1] for v in ligs.values()), 'actives')""")

md("## 5. Receptor")
code("""open('receptor.pdbqt', 'wb').write(requests.get(RECEPTOR_URL, timeout=180).content)
print('receptor.pdbqt:', os.path.getsize('receptor.pdbqt'), 'bytes')""")

md("## 6. Dock everything (checkpointed / resumable)")
code("""import csv
CKPT = 'scores.csv'
done = {}
if os.path.exists(CKPT):
    for row in csv.reader(open(CKPT)):
        if len(row) == 3:
            done[row[0]] = (float(row[1]), int(row[2]))

def dock(pq):
    out = pq.replace('.pdbqt', '_out.pdbqt')
    subprocess.run(['./vina', '--receptor', 'receptor.pdbqt', '--ligand', pq,
                    '--center_x', str(GRID_CENTER[0]), '--center_y', str(GRID_CENTER[1]), '--center_z', str(GRID_CENTER[2]),
                    '--size_x', str(BOX), '--size_y', str(BOX), '--size_z', str(BOX),
                    '--exhaustiveness', str(EXHAUSTIVENESS), '--num_modes', '3', '--cpu', '2', '--out', out],
                   capture_output=True, text=True)
    if os.path.exists(out):
        for ln in open(out):
            if ln.startswith('REMARK VINA RESULT:'):
                return float(ln.split()[3])
    return None

w = open(CKPT, 'a', newline='')
for n, (pq, lab) in tqdm(ligs.items(), desc='dock'):
    if n in done:
        continue
    v = dock(pq)
    if v is not None:
        done[n] = (v, lab)
        csv.writer(w).writerow([n, v, lab]); w.flush()
w.close()
print('docked:', len(done), 'of', len(ligs))""")

md("## 7. Enrichment metrics + ROC")
code("""import numpy as np, matplotlib.pyplot as plt
from sklearn.metrics import roc_auc_score, roc_curve
names = list(done)
y = np.array([done[n][1] for n in names])
score = -np.array([done[n][0] for n in names])   # more negative Vina = better -> higher score
auc = roc_auc_score(y, score)
def EF(frac):
    k = max(1, int(len(y) * frac))
    idx = np.argsort(-score)[:k]
    return (y[idx].sum() / y.sum()) / frac
ef1, ef5, ef10 = EF(0.01), EF(0.05), EF(0.10)
fpr, tpr, _ = roc_curve(y, score)
plt.figure(figsize=(4, 4))
plt.plot(fpr, tpr, label=f'docking AUC {auc:.2f}')
plt.plot([0, 1], [0, 1], '--', c='grey')
plt.xlabel('false positive rate'); plt.ylabel('true positive rate')
plt.title('NS5 enrichment (property-matched decoys)'); plt.legend(); plt.show()
print(f'AUC {auc:.3f} | EF1% {ef1:.1f} | EF5% {ef5:.1f} | EF10% {ef10:.1f} '
      f'| {int(y.sum())} actives, {int((1 - y).sum())} decoys')""")

md("## 8. Export the result (send this JSON back for dashboard integration)")
code("""res = {'target': 'DENV_NS5', 'method': 'property-matched DUD-E-style decoys', 'receptor': '5CCV',
       'n_actives': int(y.sum()), 'n_decoys': int((1 - y).sum()),
       'decoys_per_active': DECOYS_PER_ACTIVE, 'exhaustiveness': EXHAUSTIVENESS,
       'auc': round(float(auc), 3),
       'ef': {'1pct': round(float(ef1), 2), '5pct': round(float(ef5), 2), '10pct': round(float(ef10), 2)},
       'roc': [[round(float(a), 4), round(float(b), 4)] for a, b in zip(fpr, tpr)],
       'scores': {n: round(done[n][0], 2) for n in names}}
json.dump(res, open('ns5_enrichment_result.json', 'w'), indent=2)
try:
    from google.colab import files
    files.download('ns5_enrichment_result.json')
except Exception:
    pass
print('Saved ns5_enrichment_result.json - send it back to add a property-matched benchmark to the Validation tab.')
print('Report the AUC honestly, whatever it is - this is NS5-only (the one target with protein-specific actives).')""")

# ---- assemble + validate ----
cells = []
for ctype, src in CELLS:
    cell = {"cell_type": ctype, "metadata": {}, "source": src.splitlines(keepends=True)}
    if ctype == "code":
        cell["execution_count"] = None
        cell["outputs"] = []
        checkable = "\n".join("pass" if l.lstrip().startswith(("!", "%")) else l for l in src.splitlines())
        compile(checkable, "<cell>", "exec")  # syntax check (IPython magics -> pass)
    cells.append(cell)

nb = {"cells": cells,
      "metadata": {"colab": {"provenance": [], "toc_visible": True},
                   "kernelspec": {"name": "python3", "display_name": "Python 3"},
                   "language_info": {"name": "python"}},
      "nbformat": 4, "nbformat_minor": 0}

out = Path(__file__).resolve().parent / "ns5_enrichment_validation.ipynb"
json.dump(nb, open(out, "w"), indent=1)
print(f"wrote {out} ({len(cells)} cells, all code cells compiled OK)")
