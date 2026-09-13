#!/usr/bin/env python3
"""Generate colab/ns5_box_fix_validation.ipynb.

Re-runs the NS5 retrospective enrichment after a docking-setup defect was found:
the original run used the full 8-chain 5CCV crystal and a grid box centred in a
crystal-packing void (12 residues from 4 different chains within 12 A, nearest
atom 7.9 A, only 278 receptor atoms in the box). The ligands were effectively
docked into empty space, which explains an AUC of 0.32 without any appeal to
ligand mechanism.

This notebook docks the SAME actives and the SAME property-matched decoys against
two corrected receptors so the box is the only thing that changed:

  Arm A  5CCV chain A only, box on the RdRp catalytic site (motif A D533 + motif C GDD)
  Arm B  4V0R (2.40 A, single chain), box on motif C GDD + the catalytic Mg

Run: python3 colab/_build_box_fix_nb.py
"""
import json
from pathlib import Path

CELLS = []
def md(src): CELLS.append(("markdown", src))
def code(src): CELLS.append(("code", src))

md("""# GeneTropica - NS5 enrichment, corrected docking box

**Why this notebook exists.** The earlier NS5 benchmark reported **AUC 0.32** (worse than
a coin flip). Auditing the setup showed the cause was not ligand mechanism but the docking
box itself:

| | original run | this run (Arm A) | this run (Arm B) |
|---|---|---|---|
| receptor | 5CCV, **all 8 chains** (64,264 atoms) | 5CCV **chain A** (8,384 atoms) | **4V0R** chain A, 2.40 A (8,417 atoms) |
| box centre | (-118.9, 60.8, 40.2) | (-48.3, 35.4, 36.9) | (-11.3, 19.2, -7.8) |
| what is there | crystal-packing void: 12 residues from **4 different chains**, nearest atom **7.9 A** | RdRp catalytic site (D533 + GDD) | RdRp catalytic site (GDD + catalytic Mg) |
| receptor atoms in box | 278 | 669 | 723 |

The catalytic motifs sat **33 to 84 A outside** the original box in every chain, so the real
binding site was never searched.

**What is held constant:** the same 8 known NS5 inhibitors, the same property-matched
(DUD-E-style) decoy construction, the same exhaustiveness (8) and the same box size (25 A).
Only the receptor and the box move, so the comparison isolates the defect.

**A hard guard runs before any docking.** It refuses to dock unless the catalytic site is
inside the box and the box actually contains protein. The original setup fails that guard,
which is the point of adding it.

**Runtime.** AutoDock Vina is CPU-only. Roughly 2 to 4 h for two arms of about 58 ligands at
exhaustiveness 8. Checkpoints and results are written to **Google Drive**, so a runtime reset
resumes instead of starting over. The final JSON is also printed into the cell output.

Run via **Runtime > Run all**.""")

code("""# Setup (~2 min): RDKit, scikit-learn, SciPy, AutoDock Vina binary (CPU).
!pip -q install rdkit scikit-learn scipy requests tqdm >/dev/null 2>&1
!apt-get -qq install -y openbabel >/dev/null 2>&1
import os, subprocess, json, math, requests
if not os.path.exists('vina'):
    url = 'https://github.com/ccsb-scripps/AutoDock-Vina/releases/download/v1.2.5/vina_1.2.5_linux_x86_64'
    open('vina', 'wb').write(requests.get(url, timeout=180).content)
    os.chmod('vina', 0o755)
print('vina:', subprocess.run(['./vina', '--version'], capture_output=True, text=True).stdout.strip())""")

md("## Parameters")
code("""RAW = 'https://raw.githubusercontent.com/RyoungJKT/genetropica-v2/main'

# Two corrected receptors. 'catalytic' lists points that MUST fall inside the grid box.
# Arm A keeps the deposited numbering, so its catalytic atoms are located by residue id.
# Arm B was re-numbered by the preparation step, so its catalytic points are given as
# coordinates taken from the original 4V0R deposition (GDD centroid, and the catalytic Mg).
RECEPTORS = [
    {
        'arm': 'A',
        'label': '5CCV chain A, catalytic box',
        'pdb': '5CCV',
        'url': RAW + '/colab/5CCV_chainA.pdbqt',
        'center': [-48.3, 35.4, 36.9],
        'catalytic_resids': [533, 662, 663, 664],   # motif A D533, motif C G662-D663-D664
        'catalytic_points': [],
    },
    {
        'arm': 'B',
        'label': '4V0R 2.40 A, catalytic box',
        'pdb': '4V0R',
        'url': RAW + '/colab/4V0R_chainA.pdbqt',
        'center': [-11.3, 19.2, -7.8],
        'catalytic_resids': [],
        'catalytic_points': [[-13.0, 20.2, -5.5], [-9.6, 18.2, -10.1]],  # GDD centroid, catalytic Mg
    },
]

# The defective original setup, kept only so the guard can be shown to reject it.
ORIGINAL = {'arm': 'original', 'label': '5CCV all 8 chains, void box',
            'center': [-118.9, 60.8, 40.2], 'auc_reported': 0.32}

BOX               = 25       # A, same as the original run
EXHAUSTIVENESS    = 8        # same as the original run, so the numbers stay comparable
DECOYS_PER_ACTIVE = 25       # DUD-E uses 50; 25 keeps free-Colab runtime sane
DECOY_POOL_SIZE   = 4000     # drug-like molecules pulled from ChEMBL to match against
MIN_ATOMS_IN_BOX  = 400      # guard: the void box had only 278
MAX_CENTER_GAP    = 4.0      # guard: the void box centre was 7.9 A from any atom
os.makedirs('lig', exist_ok=True)""")

md("## Save location (Google Drive, so a reset cannot lose progress)")
code("""# Mount Google Drive so the docking checkpoints and the result JSON survive a runtime reset.
# 'Run all' PAUSES here once: click through the 'Connect to Google Drive' popup, then it continues.
WORKDIR = '.'
try:
    from google.colab import drive
    drive.mount('/content/drive')
    WORKDIR = '/content/drive/MyDrive/genetropica_ns5_boxfix'
    os.makedirs(WORKDIR, exist_ok=True)
    print('Saving checkpoints + result to Google Drive:', WORKDIR)
except Exception as e:
    print('Drive not mounted, using local disk (lost on reset):', repr(e))
print('WORKDIR =', WORKDIR)""")

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

md("""## 5. Receptors and the BOX GUARD

This is the cell that would have caught the original defect. For each receptor it checks that
the catalytic site is inside the grid box, that the box holds enough protein, and that the box
centre is not floating in a void. It raises instead of docking if any check fails.""")
code("""def read_pdbqt(path):
    atoms = []
    for l in open(path):
        if l.startswith(('ATOM', 'HETATM')):
            try:
                atoms.append((float(l[30:38]), float(l[38:46]), float(l[46:54]), l[22:27].strip()))
            except ValueError:
                pass
    return atoms

def inside(p, center, half):
    return all(abs(p[i] - center[i]) <= half for i in range(3))

def check_box(atoms, center, half, cat_points, label):
    cat_in = sum(1 for p in cat_points if inside(p, center, half))
    n_in = sum(1 for a in atoms if inside(a, center, half))
    nearest = min(math.dist(a[:3], center) for a in atoms)
    ok = (cat_in == len(cat_points) and len(cat_points) > 0
          and n_in >= MIN_ATOMS_IN_BOX and nearest <= MAX_CENTER_GAP)
    print(f"  {label}")
    print(f"    catalytic reference points inside box : {cat_in}/{len(cat_points)}")
    print(f"    receptor atoms inside box             : {n_in}  (need >= {MIN_ATOMS_IN_BOX})")
    print(f"    nearest atom to box centre            : {nearest:.1f} A  (need <= {MAX_CENTER_GAP})")
    print(f"    VERDICT                               : {'PASS' if ok else 'FAIL'}")
    return ok

half = BOX / 2.0
for r in RECEPTORS:
    r['file'] = f"receptor_{r['arm']}.pdbqt"
    open(r['file'], 'wb').write(requests.get(r['url'], timeout=300).content)
    atoms = read_pdbqt(r['file'])
    pts = list(r['catalytic_points'])
    if r['catalytic_resids']:
        want = {str(x) for x in r['catalytic_resids']}
        pts += [a[:3] for a in atoms if a[3] in want]
    r['n_atoms'] = len(atoms)
    print(f"{r['file']}: {len(atoms)} atoms  ({r['label']})")
    if not check_box(atoms, r['center'], half, pts, f"guard, arm {r['arm']}"):
        raise SystemExit(f"Box guard FAILED for arm {r['arm']}: refusing to dock.")
print('\\nAll receptors passed the box guard.')""")

md("""### The guard applied to the original, defective setup

For the record, the same guard is run against the box the first benchmark used. It is expected
to FAIL. Nothing is docked here; this cell only documents the defect.""")
code("""try:
    open('receptor_original.pdbqt', 'wb').write(
        requests.get(RAW + '/colab/5CCV_clean.pdbqt', timeout=600).content)
    atoms_o = read_pdbqt('receptor_original.pdbqt')
    print(f"receptor_original.pdbqt: {len(atoms_o)} atoms (all 8 chains)")
    # Catalytic points cannot be located unambiguously in an 8-copy file, so this reports
    # only the density and void checks, which are what the original box fails on.
    n_in = sum(1 for a in atoms_o if inside(a, ORIGINAL['center'], half))
    nearest = min(math.dist(a[:3], ORIGINAL['center']) for a in atoms_o)
    print(f"  receptor atoms inside the original box : {n_in}  (need >= {MIN_ATOMS_IN_BOX})")
    print(f"  nearest atom to the original centre    : {nearest:.1f} A  (need <= {MAX_CENTER_GAP})")
    print(f"  VERDICT                                : "
          f"{'PASS' if (n_in >= MIN_ATOMS_IN_BOX and nearest <= MAX_CENTER_GAP) else 'FAIL (as expected)'}")
except Exception as e:
    print('skipped (could not fetch the original 4.9 MB receptor):', repr(e))""")

md("## 6. Dock both arms (checkpointed per arm, resumable)")
code("""import csv
def dock(receptor, pq, center):
    out = pq.replace('.pdbqt', '_out.pdbqt')
    subprocess.run(['./vina', '--receptor', receptor, '--ligand', pq,
                    '--center_x', str(center[0]), '--center_y', str(center[1]), '--center_z', str(center[2]),
                    '--size_x', str(BOX), '--size_y', str(BOX), '--size_z', str(BOX),
                    '--exhaustiveness', str(EXHAUSTIVENESS), '--num_modes', '3', '--cpu', '2',
                    '--seed', '42', '--out', out],
                   capture_output=True, text=True)
    if os.path.exists(out):
        for ln in open(out):
            if ln.startswith('REMARK VINA RESULT:'):
                return float(ln.split()[3])
    return None

for r in RECEPTORS:
    ckpt = os.path.join(WORKDIR, f"scores_arm{r['arm']}.csv")
    done = {}
    if os.path.exists(ckpt):
        for row in csv.reader(open(ckpt)):
            if len(row) == 3:
                done[row[0]] = (float(row[1]), int(row[2]))
    w = open(ckpt, 'a', newline='')
    for n, (pq, lab) in tqdm(ligs.items(), desc=f"dock arm {r['arm']}"):
        if n in done:
            continue
        v = dock(r['file'], pq, r['center'])
        if v is not None:
            done[n] = (v, lab)
            csv.writer(w).writerow([n, v, lab]); w.flush()
    w.close()
    r['scores'] = done
    print(f"arm {r['arm']}: docked {len(done)} of {len(ligs)}  ->  {ckpt}")""")

md("""## 7. Enrichment, with uncertainty

An AUC from 8 actives is imprecise, so each arm reports a bootstrap 95% interval and a
Mann-Whitney p-value against the 0.5 null. Do not read a difference as real unless the
intervals separate.""")
code("""import numpy as np, matplotlib.pyplot as plt
from sklearn.metrics import roc_auc_score, roc_curve
rng = np.random.default_rng(0)

def auc_of(a, d):
    a = np.asarray(a); d = np.asarray(d)
    gt = (a[:, None] > d[None, :]).sum(); eq = (a[:, None] == d[None, :]).sum()
    return (gt + 0.5 * eq) / (len(a) * len(d))

plt.figure(figsize=(5, 5))
plt.plot([0, 1], [0, 1], '--', c='grey', label='random (0.50)')
for r in RECEPTORS:
    names = list(r['scores'])
    y = np.array([r['scores'][n][1] for n in names])
    score = -np.array([r['scores'][n][0] for n in names])   # more negative Vina = better
    a, d = score[y == 1], score[y == 0]
    auc = float(roc_auc_score(y, score))
    def EF(frac):
        k = max(1, int(len(y) * frac))
        idx = np.argsort(-score)[:k]
        return float((y[idx].sum() / y.sum()) / frac)
    boots = np.array([auc_of(rng.choice(a, len(a)), rng.choice(d, len(d))) for _ in range(20000)])
    lo, hi = (float(v) for v in np.percentile(boots, [2.5, 97.5]))
    try:
        from scipy.stats import mannwhitneyu
        p = float(mannwhitneyu(a, d, alternative='two-sided').pvalue)
    except Exception:
        allv = np.concatenate([a, d]); na = len(a)
        perm = np.array([auc_of(x[:na], x[na:]) for x in (rng.permutation(allv) for _ in range(20000))])
        p = float(np.mean(np.abs(perm - 0.5) >= abs(auc - 0.5)))
    r['stats'] = {'auc': round(auc, 3), 'ci95': [round(lo, 3), round(hi, 3)], 'p': round(p, 4),
                  'ef': {'1pct': round(EF(0.01), 2), '5pct': round(EF(0.05), 2), '10pct': round(EF(0.10), 2)},
                  'n_actives': int(y.sum()), 'n_decoys': int((1 - y).sum())}
    fpr, tpr, _ = roc_curve(y, score)
    r['roc'] = [[round(float(x), 4), round(float(t), 4)] for x, t in zip(fpr, tpr)]
    plt.plot(fpr, tpr, label=f"arm {r['arm']} {r['pdb']}: AUC {auc:.2f}")
    print(f"arm {r['arm']} ({r['label']}): AUC {auc:.3f}  95% CI {lo:.2f}-{hi:.2f}  p={p:.3f}  "
          f"EF1% {r['stats']['ef']['1pct']}  ({int(y.sum())} actives, {int((1-y).sum())} decoys)")
plt.xlabel('false positive rate'); plt.ylabel('true positive rate')
plt.title('NS5 enrichment with a corrected docking box'); plt.legend(); plt.show()
print(f"\\nfor reference, the original void-box run reported AUC {ORIGINAL['auc_reported']}")""")

md("## 8. Result, copy the printed JSON below")
code("""res = {
    'target': 'DENV_NS5',
    'method': 'property-matched DUD-E-style decoys, corrected docking box',
    'box_size': BOX, 'exhaustiveness': EXHAUSTIVENESS, 'decoys_per_active': DECOYS_PER_ACTIVE,
    'supersedes': {'label': ORIGINAL['label'], 'center': ORIGINAL['center'],
                   'auc_reported': ORIGINAL['auc_reported'],
                   'defect': 'grid box centred in a crystal-packing void of the 8-chain crystal; '
                             'catalytic motifs 33-84 A outside the box'},
    'arms': [{'arm': r['arm'], 'label': r['label'], 'pdb': r['pdb'], 'center': r['center'],
              'receptor_atoms': r['n_atoms'], 'stats': r['stats'], 'roc': r['roc'],
              'scores': {n: round(v[0], 2) for n, v in r['scores'].items()}}
             for r in RECEPTORS],
}
RESULT = os.path.join(WORKDIR, 'ns5_box_fix_result.json')
json.dump(res, open(RESULT, 'w'), indent=2)
print('Saved to', RESULT)
try:
    from google.colab import files
    files.download(RESULT)
except Exception:
    pass
print('\\n===================== COPY EVERYTHING BELOW THIS LINE =====================\\n')
print(json.dumps(res, indent=2))
print('\\n===================== COPY EVERYTHING ABOVE THIS LINE =====================\\n')
print('Paste the JSON above back to update the Validation tab.')
print('Report whatever the AUC turns out to be, including if it is still at or below random.')""")

# ---- assemble + validate ----
cells = []
for ctype, src in CELLS:
    cell = {"cell_type": ctype, "metadata": {}, "source": src.splitlines(keepends=True)}
    if ctype == "code":
        cell["execution_count"] = None
        cell["outputs"] = []
        checkable = "\n".join(
            ((l[:len(l) - len(l.lstrip())] + "pass") if l.lstrip().startswith(("!", "%")) else l)
            for l in src.splitlines()
        )
        compile(checkable, "<cell>", "exec")  # syntax check (IPython magics -> pass)
    cells.append(cell)

nb = {"cells": cells,
      "metadata": {"colab": {"provenance": [], "toc_visible": True},
                   "kernelspec": {"name": "python3", "display_name": "Python 3"},
                   "language_info": {"name": "python"}},
      "nbformat": 4, "nbformat_minor": 0}

out = Path(__file__).resolve().parent / "ns5_box_fix_validation.ipynb"
json.dump(nb, open(out, "w"), indent=1)
print(f"wrote {out} ({len(cells)} cells, all code cells compiled OK)")
