#!/usr/bin/env python3
"""Generate colab/ns5_ai_docking_validation.ipynb.

A head-to-head retrospective enrichment on dengue NS5: classical docking
(AutoDock Vina) versus AI co-folding (Boltz-2 affinity, and OpenFold3 confidence),
scored on the SAME 8 known actives and the same property-matched decoys, so the
AUCs are directly comparable to the original Vina result (AUC ~0.32-0.37).

Run: python3 colab/_build_ai_nb.py
"""
import json
from pathlib import Path

CELLS = []
def md(src): CELLS.append(("markdown", src))
def code(src): CELLS.append(("code", src))

md("""# GeneTropica - NS5: classical docking vs AI co-folding (head-to-head)

Does an AI method beat classical docking on the dengue **NS5** validation? Classical AutoDock Vina scored **AUC ~0.37 (below random)** here, because the true NS5 inhibitors are nucleoside analogues that dock weakly. This notebook scores the **same 8 actives and the same property-matched decoys** with three methods and compares their enrichment AUC:

1. **AutoDock Vina** (classical docking, CPU) - the baseline.
2. **Boltz-2** (AI, open MIT) - predicts a binding **affinity probability**; the reliable core of this comparison.
3. **OpenFold3** (AI co-folding, preview) - predicts the complex and a **confidence** score; flagged as preview, see note in its section.

**Honest framing:** AI co-folding is still a prediction, not a measured affinity, with known failure modes (confident but wrong poses, novel chemistry). The point is the fair, same-set comparison, reported whichever way it lands.

**Runtime:** needs a **GPU** runtime (Runtime > Change runtime type > A100 or any GPU). Vina ~1 h on CPU, Boltz-2 ~20-40 min, OpenFold3 heavier. Each method is checkpointed/resumable and prints its result, so a disconnect will not lose progress.

Run via **Runtime > Run all** (after selecting a GPU runtime).""")

code("""# Setup: confirm GPU, install RDKit / OpenBabel / Vina (CPU) / scikit-learn.
import subprocess, os, json, requests
gpu = subprocess.run(['nvidia-smi', '--query-gpu=name', '--format=csv,noheader'], capture_output=True, text=True).stdout.strip()
print('GPU:', gpu or 'NONE - select Runtime > Change runtime type > GPU (A100 ideal)')
!pip -q install rdkit scikit-learn requests tqdm pyyaml >/dev/null 2>&1
!apt-get -qq install -y openbabel >/dev/null 2>&1
if not os.path.exists('vina'):
    url = 'https://github.com/ccsb-scripps/AutoDock-Vina/releases/download/v1.2.5/vina_1.2.5_linux_x86_64'
    open('vina', 'wb').write(requests.get(url, timeout=180).content); os.chmod('vina', 0o755)
print('vina:', subprocess.run(['./vina', '--version'], capture_output=True, text=True).stdout.strip())""")

md("## Parameters")
code("""RAW = 'https://raw.githubusercontent.com/RyoungJKT/genetropica-v2/main'
RECEPTOR_URL      = RAW + '/colab/5CCV_clean.pdbqt'   # the project's exact NS5 receptor (for Vina)
NS5_PDB           = '5CCV'                            # for the protein sequence (for the AI models)
GRID_CENTER       = [-118.9, 60.8, 40.2]
BOX               = 25
EXHAUSTIVENESS    = 8
DECOYS_PER_ACTIVE = 25       # property-matched decoys per active (DUD-E style)
DECOY_POOL_SIZE   = 4000
RUN_VINA          = True     # set False to skip the classical baseline and reuse the known AUC ~0.32
os.makedirs('lig', exist_ok=True)""")

md("## Save location (Google Drive, so a reset can't lose this long run)")
code("""# Mount Google Drive so every checkpoint and the result survive a runtime reset.
# 'Run all' PAUSES here once: click through the 'Connect to Google Drive' popup, then it continues.
WORKDIR = '.'
try:
    from google.colab import drive
    drive.mount('/content/drive')
    WORKDIR = '/content/drive/MyDrive/genetropica_ns5_ai'
    os.makedirs(WORKDIR, exist_ok=True)
    print('Checkpoints + result -> Google Drive:', WORKDIR)
except Exception as e:
    print('Drive not mounted, using local disk (lost on reset):', repr(e))
print('WORKDIR =', WORKDIR)""")

md("## 1. The 8 known DENV NS5 / RdRp inhibitors (the actives)")
code("""ACTIVES = {
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
    if not mols: break
    for m in mols:
        s = (m.get('molecule_structures') or {}).get('canonical_smiles')
        if s and '.' not in s: pool.append(s)
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
    if mm is not None: poolf.append((s, feats(mm)))
def matches(a, p):
    return (abs(a['mw']-p['mw'])<=25 and abs(a['logp']-p['logp'])<=1.0 and abs(a['hbd']-p['hbd'])<=1
            and abs(a['hba']-p['hba'])<=2 and abs(a['rot']-p['rot'])<=2 and a['q']==p['q'])
used, decoys = set(), {}
for n, a in act.items():
    picked = []
    for i, (s, p) in enumerate(poolf):
        if i in used or not matches(a, p): continue
        if max(DataStructs.BulkTanimotoSimilarity(p['fp'], act_fps)) >= 0.35: continue
        picked.append(i)
        if len(picked) >= DECOYS_PER_ACTIVE: break
    used.update(picked)
    for j, i in enumerate(picked): decoys[f'decoy_{n}_{j:02d}'] = poolf[i][0]
print('property-matched decoys:', len(decoys))""")

md("## 4. The shared ligand set (the SAME molecules every method scores)")
code("""# name -> (smiles, label)  label 1 = known active, 0 = decoy
LIGANDS = {n: (s, 1) for n, s in ACTIVES.items()}
LIGANDS.update({n: (s, 0) for n, s in decoys.items()})
print('ligands to score:', len(LIGANDS), '|', sum(v[1] for v in LIGANDS.values()), 'actives,',
      sum(1 for v in LIGANDS.values() if v[1] == 0), 'decoys')""")

md("## 5. NS5 receptor: structure (for Vina) and sequence (for the AI models)")
code("""# Receptor structure for docking.
open('receptor.pdbqt', 'wb').write(requests.get(RECEPTOR_URL, timeout=180).content)
print('receptor.pdbqt:', os.path.getsize('receptor.pdbqt'), 'bytes')
# Protein sequence for co-folding: first chain of the deposited PDB.
fasta = requests.get(f'https://www.rcsb.org/fasta/entry/{NS5_PDB}', timeout=60).text
seqs, cur = [], ''
for ln in fasta.splitlines():
    if ln.startswith('>'):
        if cur: seqs.append(cur); cur = ''
    else: cur += ln.strip()
if cur: seqs.append(cur)
NS5_SEQ = max(seqs, key=len)   # the NS5 chain (longest)
print('NS5 sequence length:', len(NS5_SEQ))""")

md("## 6. Classical baseline: AutoDock Vina (checkpointed)")
code("""import csv
VINA_CKPT = os.path.join(WORKDIR, 'vina_scores.csv')   # on Drive, survives a reset
def prep(name, smiles):
    m = Chem.MolFromSmiles(smiles)
    if m is None: return None
    m = Chem.AddHs(m)
    if AllChem.EmbedMolecule(m, AllChem.ETKDGv3()) != 0: return None
    try: AllChem.MMFFOptimizeMolecule(m)
    except Exception: pass
    sdf, pq = f'lig/{name}.sdf', f'lig/{name}.pdbqt'
    Chem.MolToMolFile(m, sdf)
    subprocess.run(['obabel', sdf, '-O', pq, '--partialcharge', 'gasteiger'], capture_output=True)
    return pq if os.path.exists(pq) and os.path.getsize(pq) > 0 else None
def dock(pq):
    out = pq.replace('.pdbqt', '_out.pdbqt')
    subprocess.run(['./vina', '--receptor', 'receptor.pdbqt', '--ligand', pq,
        '--center_x', str(GRID_CENTER[0]), '--center_y', str(GRID_CENTER[1]), '--center_z', str(GRID_CENTER[2]),
        '--size_x', str(BOX), '--size_y', str(BOX), '--size_z', str(BOX),
        '--exhaustiveness', str(EXHAUSTIVENESS), '--num_modes', '3', '--cpu', '2', '--out', out], capture_output=True, text=True)
    if os.path.exists(out):
        for ln in open(out):
            if ln.startswith('REMARK VINA RESULT:'): return float(ln.split()[3])
    return None
vina = {}
if os.path.exists(VINA_CKPT):
    for r in csv.reader(open(VINA_CKPT)):
        if len(r) == 2: vina[r[0]] = float(r[1])
if RUN_VINA:
    from tqdm.auto import tqdm
    w = open(VINA_CKPT, 'a', newline='')
    for n, (smi, lab) in tqdm(LIGANDS.items(), desc='vina'):
        if n in vina: continue
        pq = prep(n, smi)
        v = dock(pq) if pq else None
        if v is not None:
            vina[n] = v; csv.writer(w).writerow([n, v]); w.flush()
    w.close()
    print('vina scored:', len(vina), 'of', len(LIGANDS))
else:
    print('RUN_VINA = False; will use the known Vina enrichment AUC ~0.32 as the baseline.')""")

md("## 7. AI method A: Boltz-2 affinity (the reliable core)")
code("""# Boltz-2: open MIT co-folding + affinity model. Score = affinity_probability_binary (0-1, higher = more likely a binder).
!pip -q install \"boltz[cuda]\" -U >/dev/null 2>&1
import yaml, glob
os.makedirs('boltz_in', exist_ok=True)
for n, (smi, lab) in LIGANDS.items():
    spec = {'version': 1,
            'sequences': [{'protein': {'id': 'A', 'sequence': NS5_SEQ}},
                          {'ligand': {'id': 'B', 'smiles': smi}}],
            'properties': [{'affinity': {'binder': 'B'}}]}
    yaml.safe_dump(spec, open(f'boltz_in/{n}.yaml', 'w'))
# Resumable by default (Boltz skips inputs already predicted). The protein MSA is fetched per run via the server.
BOLTZ_OUT = os.path.join(WORKDIR, 'boltz_out')   # on Drive; Boltz skips already-predicted inputs, so a reset resumes
print('running Boltz-2 on', len(LIGANDS), 'complexes (this is the slow GPU step; safe to re-run if it disconnects)...')
subprocess.run(['boltz', 'predict', 'boltz_in', '--use_msa_server', '--out_dir', BOLTZ_OUT,
                '--devices', '1', '--accelerator', 'gpu'])
# Collect affinity_probability_binary for each ligand.
boltz = {}
for n in LIGANDS:
    hits = glob.glob(f'{BOLTZ_OUT}/**/affinity_{n}.json', recursive=True)
    if hits:
        try: boltz[n] = json.load(open(hits[0])).get('affinity_probability_binary')
        except Exception: pass
print('boltz scored:', sum(1 for v in boltz.values() if v is not None), 'of', len(LIGANDS))""")

md("""## 8. AI method B: OpenFold3 co-folding (PREVIEW - may need a schema tweak)

OpenFold3 is a preview release. The protein-ligand query schema below follows the AlphaFold3 input it
replicates and a defensive confidence parser; if a cell errors, confirm the exact `query_json` format and
confidence field names from the OpenFold3 docs / Hugging Face examples and adjust the two marked lines.
This section is wrapped so a failure here does not affect the Vina or Boltz-2 results above.
Docs: https://openfold-3.readthedocs.io  |  examples: https://huggingface.co/OpenFold/OpenFold3""")
code("""import csv as _csv
OF3_OUT = os.path.join(WORKDIR, 'of3_out')
OF3_CKPT = os.path.join(WORKDIR, 'of3_scores.csv')   # on Drive, survives a reset
of3 = {}
if os.path.exists(OF3_CKPT):
    for r in _csv.reader(open(OF3_CKPT)):
        if len(r) == 2:
            try: of3[r[0]] = float(r[1])
            except Exception: pass
RUN_OPENFOLD3 = True   # set False to skip
if RUN_OPENFOLD3:
  try:
    !pip -q install openfold3 -U >/dev/null 2>&1
    subprocess.run(['setup_openfold'])   # downloads weights (a few GB; one time)
    os.makedirs('of3_in', exist_ok=True); os.makedirs(OF3_OUT, exist_ok=True)
    from tqdm.auto import tqdm
    def of3_confidence(d):
        for k in ('ranking_score', 'ranking_confidence', 'iptm', 'ptm'):
            if isinstance(d, dict) and d.get(k) is not None: return float(d[k])
        pl = d.get('plddt') if isinstance(d, dict) else None        # fall back to mean pLDDT
        if isinstance(pl, list) and pl: return sum(pl) / len(pl)
        return None
    w3 = open(OF3_CKPT, 'a', newline='')
    for n, (smi, lab) in tqdm(LIGANDS.items(), desc='openfold3'):
        if n in of3: continue
        # ---- query schema (AF3-style); ADJUST if the preview differs ----
        q = {'name': n, 'modelSeeds': [1],
             'sequences': [{'protein': {'id': 'A', 'sequence': NS5_SEQ}},
                           {'ligand': {'id': 'L', 'smiles': smi}}]}
        json.dump(q, open(f'of3_in/{n}.json', 'w'))
        try:
            subprocess.run(['run_openfold', 'predict', f'--query_json=of3_in/{n}.json',
                            f'--output_dir={OF3_OUT}', '--use_msa_server'], capture_output=True, text=True, timeout=1200)
            import glob as _g
            cj = _g.glob(f'{OF3_OUT}/**/*{n}*conf*.json', recursive=True) or _g.glob(f'{OF3_OUT}/**/*{n}*.json', recursive=True)
            sc = of3_confidence(json.load(open(cj[0]))) if cj else None
        except Exception:
            sc = None
        of3[n] = sc
        if sc is not None:
            _csv.writer(w3).writerow([n, sc]); w3.flush()
    w3.close()
    print('openfold3 scored:', sum(1 for v in of3.values() if v is not None), 'of', len(LIGANDS))
  except Exception as e:
    print('OpenFold3 section did not run cleanly (preview):', repr(e))
    print('The Vina and Boltz-2 comparison below is unaffected. Adjust the query schema and re-run this cell.')
else:
    print('OpenFold3 skipped (RUN_OPENFOLD3 = False).')""")

md("## 9. Head-to-head: enrichment AUC + ROC, and export")
code("""import numpy as np, matplotlib.pyplot as plt
from sklearn.metrics import roc_auc_score, roc_curve
labels = {n: lab for n, (smi, lab) in LIGANDS.items()}
def metrics(scoremap, higher_is_better):
    names = [n for n in scoremap if scoremap[n] is not None and n in labels]
    if not names: return None
    y = np.array([labels[n] for n in names])
    s = np.array([scoremap[n] for n in names], dtype=float)
    if not higher_is_better: s = -s            # Vina: more negative is better
    if y.sum() == 0 or y.sum() == len(y): return None
    auc = roc_auc_score(y, s)
    def EF(frac):
        k = max(1, int(len(y) * frac)); idx = np.argsort(-s)[:k]
        return round(float((y[idx].sum() / y.sum()) / frac), 2)
    fpr, tpr, _ = roc_curve(y, s)
    return {'auc': round(float(auc), 3), 'n': len(y), 'nActives': int(y.sum()),
            'ef': {'1pct': EF(0.01), '5pct': EF(0.05), '10pct': EF(0.10)},
            'roc': [[round(float(a), 4), round(float(b), 4)] for a, b in zip(fpr, tpr)]}
results = {}
mv = metrics(vina, higher_is_better=False) if vina else None
if mv: results['vina'] = mv
elif not RUN_VINA: results['vina'] = {'auc': 0.32, 'note': 'known property-matched enrichment from the Vina notebook'}
mb = metrics(boltz, higher_is_better=True)
if mb: results['boltz2'] = mb
mo = metrics(of3, higher_is_better=True)
if mo: results['openfold3'] = mo

plt.figure(figsize=(4.4, 4.4))
COL = {'vina': '#888', 'boltz2': '#1F5740', 'openfold3': '#A8492B'}
for k, r in results.items():
    if 'roc' in r: plt.plot([p[0] for p in r['roc']], [p[1] for p in r['roc']], color=COL.get(k), label=f'{k} AUC {r[\"auc\"]}')
plt.plot([0, 1], [0, 1], '--', c='lightgray')
plt.xlabel('false positive rate'); plt.ylabel('true positive rate')
plt.title('NS5: classical docking vs AI co-folding'); plt.legend(); plt.show()

out = {'target': 'DENV_NS5', 'comparison': 'classical docking vs AI co-folding',
       'receptor': '5CCV', 'decoys_per_active': DECOYS_PER_ACTIVE, 'methods': results}
RESULT = os.path.join(WORKDIR, 'ns5_ai_headtohead_result.json')
json.dump(out, open(RESULT, 'w'), indent=2)
print('saved to', RESULT)
try:
    from google.colab import files; files.download(RESULT)
except Exception: pass
print('\\n===================== COPY EVERYTHING BELOW THIS LINE =====================\\n')
print(json.dumps(out, indent=2))
print('\\n===================== COPY EVERYTHING ABOVE THIS LINE =====================\\n')
print('Paste the JSON above back to add the classical-vs-AI head-to-head to the Validation tab.')
print('Report every AUC honestly, whatever it is. AI co-folding is a prediction, not a measured affinity.')""")

# ---- assemble + validate ----
cells = []
for ctype, src in CELLS:
    cell = {"cell_type": ctype, "metadata": {}, "source": src.splitlines(keepends=True)}
    if ctype == "code":
        cell["execution_count"] = None
        cell["outputs"] = []
        checkable = "\n".join(((l[:len(l) - len(l.lstrip())] + "pass") if l.lstrip().startswith(("!", "%")) else l) for l in src.splitlines())
        compile(checkable, "<cell>", "exec")
    cells.append(cell)
nb = {"cells": cells,
      "metadata": {"colab": {"provenance": [], "toc_visible": True},
                   "accelerator": "GPU",
                   "kernelspec": {"name": "python3", "display_name": "Python 3"},
                   "language_info": {"name": "python"}},
      "nbformat": 4, "nbformat_minor": 0}
out = Path(__file__).resolve().parent / "ns5_ai_docking_validation.ipynb"
json.dump(nb, open(out, "w"), indent=1)
print(f"wrote {out} ({len(cells)} cells, all code cells compiled OK)")
