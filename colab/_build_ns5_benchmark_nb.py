#!/usr/bin/env python3
"""Generate colab/ns5_receptor_benchmark.ipynb.

A retrospective enrichment benchmark for dengue NS5: 8 known RdRp inhibitors against
property-matched (DUD-E-style) decoys, docked with AutoDock Vina into two independently
prepared receptors so that receptor choice is the only variable.

  Arm A  5CCV chain A, box on the RdRp catalytic site (motif A D533 + motif C GDD)
  Arm B  4V0R at 2.40 A, box on motif C GDD + the catalytic Mg

Receptors are read from Google Drive, so the notebook needs no access to any code host.

Run: python3 colab/_build_ns5_benchmark_nb.py
"""
import json
from pathlib import Path

CELLS = []
def md(src): CELLS.append(("markdown", src))
def code(src): CELLS.append(("code", src))

md("""# Dengue NS5, retrospective enrichment benchmark

Does AutoDock Vina rank **known** NS5 polymerase inhibitors above look-alike molecules that
are not known to work? That is the only fair way to find out whether a docking score means
anything for this target before trusting it on untested drugs.

**Design.** 8 published NS5 / RdRp inhibitors are hidden among property-matched decoys:
each decoy is matched to an active on molecular weight, logP, hydrogen-bond donors and
acceptors, rotatable bonds and formal charge, while being topologically dissimilar
(Morgan-fingerprint Tanimoto below 0.35). Everything is docked and ranked by score. A method
that works puts the real inhibitors near the top.

**Two receptors, because receptor preparation matters as much as the scoring function:**

| | Arm A | Arm B |
|---|---|---|
| structure | 5CCV, chain A | 4V0R |
| resolution | 3.60 A | **2.40 A** |
| box centre | (-48.3, 35.4, 36.9) | (-11.3, 19.2, -7.8) |
| centred on | motif A D533 with motif C GDD | motif C GDD with the catalytic Mg |

Both arms dock the **same ligands** with the same box size and the same exhaustiveness, so any
difference is attributable to the receptor.

**A box guard runs before any docking.** It refuses to proceed unless the catalytic site is
actually inside the search box and the box actually contains protein. Docking into a pocket
that does not contain the catalytic machinery produces confident, meaningless scores, so this
is checked rather than assumed.

**Reporting.** An AUC computed from 8 actives is imprecise, so each arm reports a bootstrap
95% interval and a Mann-Whitney p-value against the 0.5 null. A result is only meaningful if
the interval separates from random.

**Runtime.** AutoDock Vina is CPU-only, no GPU needed. Roughly 2 to 4 hours for two arms of
about 58 ligands at exhaustiveness 8. Docking checkpoints and the final result are written to
**Google Drive**, so a runtime reset resumes instead of starting over.

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

md("""## Google Drive

Checkpoints and results are saved here so a runtime reset does not lose progress. The two
receptor files are also read from here, so this notebook does not depend on any code host.""")
code("""# 'Run all' PAUSES here once: click through the 'Connect to Google Drive' popup, then it continues.
DRIVE_DIR = '/content/drive/MyDrive/genetropica_ns5_benchmark'
WORKDIR, RECEPTOR_DIR = '.', 'receptors'
try:
    from google.colab import drive
    drive.mount('/content/drive')
    WORKDIR = DRIVE_DIR
    RECEPTOR_DIR = os.path.join(DRIVE_DIR, 'receptors')
    os.makedirs(RECEPTOR_DIR, exist_ok=True)
    print('Drive mounted.')
except Exception as e:
    os.makedirs(RECEPTOR_DIR, exist_ok=True)
    print('Drive not mounted, using local disk (lost on reset):', repr(e))
print('WORKDIR      =', WORKDIR)
print('RECEPTOR_DIR =', RECEPTOR_DIR)""")

md("""## Parameters

`EXHAUSTIVENESS` is Vina's sampling effort. 8 is the default; raising it costs linear time and
makes scores more reproducible.""")
code("""RECEPTORS = [
    {
        'arm': 'A',
        'label': '5CCV chain A, 3.60 A',
        'pdb': '5CCV',
        'filename': '5CCV_chainA.pdbqt',
        'center': [-48.3, 35.4, 36.9],
        'catalytic_resids': [533, 662, 663, 664],   # motif A D533, motif C G662-D663-D664
        'catalytic_points': [],
    },
    {
        'arm': 'B',
        'label': '4V0R, 2.40 A',
        'pdb': '4V0R',
        'filename': '4V0R_chainA.pdbqt',
        'center': [-11.3, 19.2, -7.8],
        'catalytic_resids': [],                      # renumbered during preparation
        'catalytic_points': [[-13.0, 20.2, -5.5], [-9.6, 18.2, -10.1]],  # GDD centroid, catalytic Mg
    },
]

BOX               = 25       # A, cube side
EXHAUSTIVENESS    = 8        # Vina default
DECOYS_PER_ACTIVE = 25       # DUD-E uses 50; 25 keeps free-Colab runtime sane
DECOY_POOL_SIZE   = 4000     # drug-like molecules pulled from ChEMBL to match against
SEED              = 42       # fixed so the run is reproducible
MIN_ATOMS_IN_BOX  = 400      # guard: a box on a real pocket holds far more than this
MAX_CENTER_GAP    = 4.0      # guard: a box centre in a cavity is within a few A of protein
MIN_POOL          = 2000     # refuse to build decoys from a truncated ChEMBL pool
MIN_DECOYS_PER_ACTIVE = 5    # refuse to benchmark on too few decoys
os.makedirs('lig', exist_ok=True)""")

md("""## Receptors

Upload the two prepared receptor files to the `receptors` folder shown above, once. If they
are not found there, the next cell offers a direct upload instead.""")
code("""from pathlib import Path
missing = [r['filename'] for r in RECEPTORS
           if not os.path.exists(os.path.join(RECEPTOR_DIR, r['filename']))]
if missing:
    print('Not found in', RECEPTOR_DIR)
    for m in missing:
        print('   missing:', m)
    print('\\nUpload them now (or copy them into that Drive folder and re-run this cell).')
    try:
        from google.colab import files
        up = files.upload()
        for name, blob in up.items():
            open(os.path.join(RECEPTOR_DIR, name), 'wb').write(blob)
            print('saved to Drive:', name)
    except Exception as e:
        print('upload unavailable:', repr(e))

for r in RECEPTORS:
    r['file'] = os.path.join(RECEPTOR_DIR, r['filename'])
    size = os.path.getsize(r['file']) if os.path.exists(r['file']) else 0
    print(f"arm {r['arm']}  {r['filename']}  {size/1024:.0f} KB  ({r['label']})")
    if not size:
        raise SystemExit(f"Receptor missing for arm {r['arm']}: {r['file']}")""")

md("""## Box guard

Checks, for each receptor, that the catalytic site falls inside the search box, that the box
holds a sensible amount of protein, and that the box centre is not sitting in open solvent.
It raises rather than docking if any check fails.""")
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

half = BOX / 2.0
for r in RECEPTORS:
    atoms = read_pdbqt(r['file'])
    pts = list(r['catalytic_points'])
    if r['catalytic_resids']:
        want = {str(x) for x in r['catalytic_resids']}
        pts += [a[:3] for a in atoms if a[3] in want]
    cat_in = sum(1 for p in pts if inside(p, r['center'], half))
    n_in = sum(1 for a in atoms if inside(a, r['center'], half))
    nearest = min(math.dist(a[:3], r['center']) for a in atoms)
    ok = (len(pts) > 0 and cat_in == len(pts)
          and n_in >= MIN_ATOMS_IN_BOX and nearest <= MAX_CENTER_GAP)
    r['n_atoms'] = len(atoms)
    print(f"arm {r['arm']} ({r['label']}): {len(atoms)} atoms")
    print(f"   catalytic reference points inside box : {cat_in}/{len(pts)}")
    print(f"   receptor atoms inside box             : {n_in}  (need >= {MIN_ATOMS_IN_BOX})")
    print(f"   nearest atom to box centre            : {nearest:.1f} A  (need <= {MAX_CENTER_GAP})")
    print(f"   VERDICT                               : {'PASS' if ok else 'FAIL'}")
    if not ok:
        raise SystemExit(f"Box guard FAILED for arm {r['arm']}: refusing to dock.")
print('\\nBoth receptors passed the box guard.')""")

md("## 1. The 8 known DENV NS5 / RdRp inhibitors (the actives)")
code("""# Nucleoside analogues and prodrugs with reported anti-NS5 activity.
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

md("""## 2. Drug-like pool from ChEMBL (to draw decoys from)

Fetched once and **cached to Drive**, so a re-run loads the cache instead of calling ChEMBL
again. That makes the run immune to a second outage and keeps the decoy set identical between
runs.

ChEMBL occasionally answers a burst of requests with an HTML error page or an empty body rather
than JSON. Calling `.json()` on that raises `JSONDecodeError`, so each request is status-checked
and retried with backoff. If the pool still comes back short, the cell **stops** rather than
quietly building a benchmark on a truncated dataset.""")
code("""import time
from rdkit import Chem, RDLogger
RDLogger.DisableLog('rdApp.*')
POOL_CACHE = os.path.join(WORKDIR, 'chembl_pool.json')

def fetch_json(url, tries=5):
    \"\"\"GET and parse JSON, retrying transient ChEMBL failures instead of crashing.\"\"\"
    hdrs = {'User-Agent': 'genetropica-ns5-benchmark/1.0', 'Accept': 'application/json'}
    last = None
    for attempt in range(1, tries + 1):
        try:
            r = requests.get(url, headers=hdrs, timeout=120)
            if r.status_code != 200:
                last = f'HTTP {r.status_code}'
            elif 'json' not in r.headers.get('Content-Type', '').lower():
                last = f"non-JSON response ({r.headers.get('Content-Type')!r}): {r.text[:80]!r}"
            else:
                return r.json()
        except Exception as e:
            last = f'{type(e).__name__}: {e}'
        if attempt < tries:
            wait = 2 ** attempt
            print(f'   attempt {attempt}/{tries} failed ({last}); retrying in {wait}s')
            time.sleep(wait)
    raise SystemExit(f'ChEMBL failed after {tries} attempts.\\n  url: {url}\\n  last error: {last}')

if os.path.exists(POOL_CACHE):
    pool = json.load(open(POOL_CACHE))
    print(f'loaded cached pool: {len(pool)} SMILES from {POOL_CACHE}')
else:
    pool = []
    url = ('https://www.ebi.ac.uk/chembl/api/data/molecule.json'
           '?molecule_properties__full_mwt__gte=250&molecule_properties__full_mwt__lte=600'
           '&limit=1000&offset=0')
    while url and len(pool) < DECOY_POOL_SIZE:
        d = fetch_json(url)
        for m in d.get('molecules', []):
            s = (m.get('molecule_structures') or {}).get('canonical_smiles')
            if s and '.' not in s:
                pool.append(s)
        print(f'   pool: {len(pool)}/{DECOY_POOL_SIZE}')
        nxt = (d.get('page_meta') or {}).get('next')
        url = 'https://www.ebi.ac.uk' + nxt if nxt else None
    json.dump(pool, open(POOL_CACHE, 'w'))
    print(f'fetched pool: {len(pool)} SMILES, cached to {POOL_CACHE}')

if len(pool) < MIN_POOL:
    raise SystemExit(
        f'Pool is only {len(pool)} SMILES, below MIN_POOL={MIN_POOL}. Refusing to continue: '
        'a truncated pool yields too few property-matched decoys and would silently produce '
        f'an underpowered benchmark. Delete {POOL_CACHE} and re-run to try again.')
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
need = MIN_DECOYS_PER_ACTIVE * len(ACTIVES)
if len(decoys) < need:
    raise SystemExit(
        f'Only {len(decoys)} decoys for {len(ACTIVES)} actives, below the required {need}. '
        'Refusing to continue, since too few decoys makes the AUC meaningless. Raise '
        'DECOY_POOL_SIZE, or loosen the property-matching tolerances deliberately.')""")

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

md("## 5. Dock both arms (checkpointed per arm, resumable)")
code("""import csv
def dock(receptor, pq, center):
    out = pq.replace('.pdbqt', '_out.pdbqt')
    subprocess.run(['./vina', '--receptor', receptor, '--ligand', pq,
                    '--center_x', str(center[0]), '--center_y', str(center[1]), '--center_z', str(center[2]),
                    '--size_x', str(BOX), '--size_y', str(BOX), '--size_z', str(BOX),
                    '--exhaustiveness', str(EXHAUSTIVENESS), '--num_modes', '3', '--cpu', '2',
                    '--seed', str(SEED), '--out', out],
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

md("""## 6. Enrichment, with uncertainty

AUC is the chance that a randomly chosen active outranks a randomly chosen decoy. 1.0 is
perfect, 0.5 is a coin flip. With only 8 actives the estimate is imprecise, so read the
interval, not the point estimate.""")
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
plt.title('Dengue NS5 retrospective enrichment'); plt.legend(); plt.show()""")

md("## 7. Result, copy the printed JSON below")
code("""res = {
    'target': 'DENV_NS5',
    'method': 'retrospective enrichment, property-matched DUD-E-style decoys',
    'box_size': BOX, 'exhaustiveness': EXHAUSTIVENESS,
    'decoys_per_active': DECOYS_PER_ACTIVE, 'seed': SEED,
    'arms': [{'arm': r['arm'], 'label': r['label'], 'pdb': r['pdb'], 'center': r['center'],
              'receptor_atoms': r['n_atoms'], 'stats': r['stats'], 'roc': r['roc'],
              'scores': {n: round(v[0], 2) for n, v in r['scores'].items()}}
             for r in RECEPTORS],
}
RESULT = os.path.join(WORKDIR, 'ns5_receptor_benchmark_result.json')
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
print('Report the AUC that comes out, including if it is at or below random.')""")

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

out = Path(__file__).resolve().parent / "ns5_receptor_benchmark.ipynb"
json.dump(nb, open(out, "w"), indent=1)
print(f"wrote {out} ({len(cells)} cells, all code cells compiled OK)")
