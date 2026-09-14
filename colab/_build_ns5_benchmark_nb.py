#!/usr/bin/env python3
"""Generate colab/ns5_receptor_benchmark.ipynb.

A retrospective enrichment benchmark for dengue NS5. 8 known RdRp inhibitors are hidden among
property-matched (DUD-E-style) decoys and ranked by AutoDock Vina score.

The two arms differ ONLY in whether the catalytic magnesium is present, so the comparison
isolates the metal:

  Arm Mg    4V0R (2.40 A) with the catalytic Mg2+ retained
  Arm noMg  4V0R (2.40 A) with the metal stripped

Three design fixes over the previous run:
  1. The catalytic Mg2+ is kept in one arm. Vina types it as a metal and it measurably changes
     the score of the one active that carries formal charge.
  2. Ligands are deprotonated at phosphate and carboxylic-acid groups only, with charges written
     by EEM, which preserves formal charge (Gasteiger silently neutralises anions).
  3. Every ligand is docked with 3 seeds; ranking uses the mean and the per-ligand spread is
     reported, so sampling noise is measured rather than assumed.

Decoys are balanced: a fixed count per active, drawn from a pool whose floor is low enough that
the smallest actives can be matched.

Run: python3 colab/_build_ns5_benchmark_nb.py
"""
import json
from pathlib import Path

CELLS = []
def md(src): CELLS.append(("markdown", src))
def code(src): CELLS.append(("code", src))

md("""# Dengue NS5, retrospective enrichment benchmark

Does AutoDock Vina rank **known** NS5 polymerase inhibitors above look-alike molecules that are
not known to work? That is the only fair way to decide whether a docking score means anything
for this target before trusting it on untested drugs.

**Design.** 8 published NS5 / RdRp inhibitors are hidden among property-matched decoys. Each
decoy matches an active on molecular weight, logP, hydrogen-bond donors and acceptors, rotatable
bonds and formal charge, while being topologically dissimilar (Morgan Tanimoto below 0.35).
Everything is docked and ranked. A method that works puts the real inhibitors near the top.

**The two arms differ only in the catalytic metal:**

| | Arm Mg | Arm noMg |
|---|---|---|
| structure | 4V0R, 2.40 A, chain A | 4V0R, 2.40 A, chain A |
| catalytic Mg2+ | **retained** | stripped |
| box centre | (-11.3, 19.2, -7.8) | (-11.3, 19.2, -7.8) |

Same receptor, same box, same ligands, same seeds. So any difference is attributable to the
magnesium, which normally coordinates the phosphate groups these drugs carry.

**Three things this run fixes.**

1. **The metal.** Stripping Mg2+ removes exactly the interaction a phosphate-bearing ligand
   depends on. Vina does type magnesium, so it can be kept.
2. **Protonation.** Ligands are deprotonated at phosphate and carboxylic-acid groups only, and
   charges are written with EEM. Gasteiger silently neutralises anions, and a blanket pH filter
   over-deprotonates (it strips sugar hydroxyls, which is wrong chemistry). Of these 8 actives
   only gs_461203, the active diphosphate species, should carry charge; the rest, including the
   sofosbuvir and balapiravir **prodrugs**, are correctly neutral.
3. **Sampling.** 3 seeds per ligand, ranked on the mean, with the spread reported. This is what
   answers "was the earlier result just noise?"

**Reporting.** Each arm gives ROC-AUC with a bootstrap 95% interval and a Mann-Whitney p-value,
**plus a stratified AUC** in which every active is compared only against its own matched decoys.
The stratified number is the one to trust, because it cannot be skewed by the decoy set happening
to contain more large molecules than the active set.

**Runtime.** Vina is CPU-only, no GPU. Two arms, 3 seeds, so expect roughly 8 to 10 hours.
Everything is checkpointed to Drive per arm and per seed, so a runtime reset resumes instead of
restarting. Run via **Runtime > Run all**.""")

code("""# Setup (~2 min): RDKit, scikit-learn, SciPy, AutoDock Vina binary (CPU).
!pip -q install rdkit scikit-learn scipy requests tqdm >/dev/null 2>&1
!apt-get -qq install -y openbabel >/dev/null 2>&1
import os, subprocess, json, math, time, requests
if not os.path.exists('vina'):
    url = 'https://github.com/ccsb-scripps/AutoDock-Vina/releases/download/v1.2.5/vina_1.2.5_linux_x86_64'
    open('vina', 'wb').write(requests.get(url, timeout=180).content)
    os.chmod('vina', 0o755)
print('vina:', subprocess.run(['./vina', '--version'], capture_output=True, text=True).stdout.strip())""")

md("""## Google Drive

Checkpoints and results are saved here so a runtime reset does not lose progress. The receptor
files are read from here too, so this notebook does not depend on any code host.""")
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

md("## Parameters")
code("""# Both arms share the box; only the receptor file differs (Mg2+ retained vs stripped).
CENTER = [-11.3, 19.2, -7.8]          # motif C GDD centroid with the catalytic Mg
CATALYTIC = [[-13.0, 20.2, -5.5],     # GDD centroid, from the 4V0R deposition
             [-9.6, 18.2, -10.1]]     # catalytic Mg position
RECEPTORS = [
    {'arm': 'Mg',   'label': '4V0R 2.40 A, catalytic Mg2+ retained',
     'filename': '4V0R_chainA_Mg.pdbqt', 'center': CENTER, 'catalytic_points': CATALYTIC},
    {'arm': 'noMg', 'label': '4V0R 2.40 A, metal stripped',
     'filename': '4V0R_chainA.pdbqt',    'center': CENTER, 'catalytic_points': CATALYTIC},
]

BOX               = 25            # A, cube side
EXHAUSTIVENESS    = 8             # kept at 8 so numbers stay comparable with the earlier run
SEEDS             = [42, 7, 1234] # 3 seeds per ligand; ranking uses the mean
DECOYS_PER_ACTIVE = 10            # balanced across actives, unlike the earlier 24/12/5/4/3/2/0/0
POOL_MW_MIN       = 200           # was 250, which made ribavirin (244) impossible to match
POOL_MW_MAX       = 600
DECOY_POOL_SIZE   = 6000
MIN_POOL          = 2000          # refuse to build decoys from a truncated ChEMBL pool
MIN_DECOYS_PER_ACTIVE = 5         # an active below this is excluded and reported
MIN_ATOMS_IN_BOX  = 400           # box guard: a real pocket holds far more than this
MAX_CENTER_GAP    = 4.0           # box guard: a centre in a cavity is within a few A of protein
os.makedirs('lig', exist_ok=True)""")

md("""## Receptors

Upload both receptor files to the `receptors` folder shown above, once. If they are missing, the
next cell offers a direct upload.""")
code("""missing = [r['filename'] for r in RECEPTORS
           if not os.path.exists(os.path.join(RECEPTOR_DIR, r['filename']))]
if missing:
    print('Not found in', RECEPTOR_DIR)
    for m in missing:
        print('   missing:', m)
    print('\\nUpload them now, or copy them into that Drive folder and re-run this cell.')
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
    print(f"arm {r['arm']:5s} {r['filename']:24s} {size/1024:6.0f} KB  ({r['label']})")
    if not size:
        raise SystemExit(f"Receptor missing for arm {r['arm']}: {r['file']}")""")

md("""## Box guard

Checks that the catalytic site falls inside the search box, that the box holds a sensible amount
of protein, and that the centre is not in open solvent. It raises rather than docking if any
check fails. It also confirms the Mg arm really does contain a magnesium atom.""")
code("""def read_pdbqt(path):
    atoms = []
    for l in open(path):
        if l.startswith(('ATOM', 'HETATM')):
            try:
                atoms.append((float(l[30:38]), float(l[38:46]), float(l[46:54]),
                              l[22:27].strip(), l[77:79].strip()))
            except ValueError:
                pass
    return atoms

def inside(p, center, half):
    return all(abs(p[i] - center[i]) <= half for i in range(3))

half = BOX / 2.0
for r in RECEPTORS:
    atoms = read_pdbqt(r['file'])
    cat_in = sum(1 for p in r['catalytic_points'] if inside(p, r['center'], half))
    n_in = sum(1 for a in atoms if inside(a, r['center'], half))
    nearest = min(math.dist(a[:3], r['center']) for a in atoms)
    metals = [a for a in atoms if a[4] in ('Mg', 'MG')]
    expect_metal = (r['arm'] == 'Mg')
    ok = (cat_in == len(r['catalytic_points']) and n_in >= MIN_ATOMS_IN_BOX
          and nearest <= MAX_CENTER_GAP and (len(metals) > 0) == expect_metal)
    r['n_atoms'] = len(atoms)
    r['n_metals'] = len(metals)
    print(f"arm {r['arm']} ({r['label']}): {len(atoms)} atoms")
    print(f"   catalytic points inside box : {cat_in}/{len(r['catalytic_points'])}")
    print(f"   atoms inside box            : {n_in}  (need >= {MIN_ATOMS_IN_BOX})")
    print(f"   nearest atom to centre      : {nearest:.1f} A  (need <= {MAX_CENTER_GAP})")
    print(f"   Mg atoms present            : {len(metals)}  (expected {'>=1' if expect_metal else '0'})")
    print(f"   VERDICT                     : {'PASS' if ok else 'FAIL'}")
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
again. ChEMBL occasionally answers a burst with an HTML error page rather than JSON, so each
request is status-checked and retried with backoff. A short pool **stops** the run rather than
quietly yielding a thin decoy set.""")
code("""from rdkit import Chem, RDLogger
RDLogger.DisableLog('rdApp.*')
POOL_CACHE = os.path.join(WORKDIR, f'chembl_pool_{POOL_MW_MIN}_{POOL_MW_MAX}.json')

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
           f'?molecule_properties__full_mwt__gte={POOL_MW_MIN}'
           f'&molecule_properties__full_mwt__lte={POOL_MW_MAX}&limit=1000&offset=0')
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
        f'a truncated pool yields too few decoys. Delete {POOL_CACHE} and re-run.')
print('pool SMILES:', len(pool))""")

md("""## 3. Balanced, property-matched decoys

Every active gets the **same** number of decoys. The earlier run was badly skewed (24 decoys for
sofosbuvir, none at all for ribavirin and galidesivir), which loaded the decoy side with large
molecules. Any active that still cannot be matched is excluded from the benchmark and named.""")
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
print('pool featurised:', len(poolf))

def matches(a, p, mw_tol=25, logp_tol=1.0):
    return (abs(a['mw'] - p['mw']) <= mw_tol and abs(a['logp'] - p['logp']) <= logp_tol
            and abs(a['hbd'] - p['hbd']) <= 1 and abs(a['hba'] - p['hba']) <= 2
            and abs(a['rot'] - p['rot']) <= 2 and a['q'] == p['q'])

used, decoys, per_active, dropped = set(), {}, {}, []
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
    per_active[n] = len(picked)
    for j, i in enumerate(picked):
        decoys[f'decoy_{n}_{j:02d}'] = poolf[i][0]

for n, c in per_active.items():
    flag = '' if c >= MIN_DECOYS_PER_ACTIVE else '   <-- EXCLUDED, too few matches'
    print(f'   {n:30s} {c:3d} decoys{flag}')
    if c < MIN_DECOYS_PER_ACTIVE:
        dropped.append(n)
for n in dropped:
    ACTIVES.pop(n, None)
    for k in [k for k in decoys if k.startswith(f'decoy_{n}_')]:
        decoys.pop(k)
print(f'\\nusable actives: {len(ACTIVES)} | decoys: {len(decoys)}')
if dropped:
    print('excluded (cannot be fairly evaluated):', dropped)
if len(ACTIVES) < 4:
    raise SystemExit(f'Only {len(ACTIVES)} actives could be matched. Refusing to continue.')""")

md("""## 4. Ligand prep, with correct protonation and charge

Phosphate and carboxylic-acid groups are deprotonated; nothing else is touched. Charges are
written by **EEM**, which preserves formal charge. Gasteiger writes a net of zero even for an
anion, which would quietly discard the charge state.""")
code("""ACID_PATTERNS = [Chem.MolFromSmarts('[$([OX2H1])]-[PX4]=[OX1]'),
                 Chem.MolFromSmarts('[CX3](=O)[OX2H1]')]

def deprotonate(smi):
    \"\"\"Deprotonate phosphate/phosphonate and carboxylic acid OH only.\"\"\"
    m = Chem.MolFromSmiles(smi)
    if m is None:
        return None
    rw = Chem.RWMol(m)
    for patt in ACID_PATTERNS:
        for match in m.GetSubstructMatches(patt):
            for idx in match:
                a = rw.GetAtomWithIdx(idx)
                if a.GetSymbol() == 'O' and a.GetTotalNumHs() > 0 and a.GetFormalCharge() == 0:
                    a.SetNoImplicit(True); a.SetNumExplicitHs(0); a.SetFormalCharge(-1)
    out = rw.GetMol()
    try:
        Chem.SanitizeMol(out)
    except Exception:
        return m
    return out

def net_charge_in(pdbqt):
    tot = 0.0
    for l in open(pdbqt):
        if l.startswith(('ATOM', 'HETATM')):
            try:
                tot += float(l[70:76])
            except ValueError:
                pass
    return tot

def prep(name, smiles):
    m = deprotonate(smiles)
    if m is None:
        return None, None
    formal = Chem.GetFormalCharge(m)
    m = Chem.AddHs(m)
    if AllChem.EmbedMolecule(m, AllChem.ETKDGv3()) != 0:
        return None, None
    try:
        AllChem.MMFFOptimizeMolecule(m)
    except Exception:
        pass
    sdf = f'lig/{name}.sdf'
    Chem.MolToMolFile(m, sdf)
    pq = f'lig/{name}.pdbqt'
    subprocess.run(['obabel', sdf, '-O', pq, '--partialcharge', 'eem'], capture_output=True)
    if not (os.path.exists(pq) and os.path.getsize(pq) > 0):
        return None, None
    return pq, formal

from tqdm.auto import tqdm
ligs, charged = {}, []
for n, s in tqdm({**ACTIVES, **decoys}.items(), desc='prep'):
    pq, formal = prep(n, s)
    if pq:
        ligs[n] = (pq, 1 if n in ACTIVES else 0)
        if formal:
            charged.append((n, formal, round(net_charge_in(pq), 2)))
print('prepared:', len(ligs), '|', sum(v[1] for v in ligs.values()), 'actives')
print('\\nligands carrying formal charge (name, formal, net charge written to pdbqt):')
for c in charged:
    print('   ', c)
if not charged:
    print('    none - expected for a set of neutral nucleosides and prodrugs')""")

md("""## 5. Dock both arms, 3 seeds each (checkpointed and resumable)

Every ligand is docked once per seed. Ranking later uses the **mean** across seeds, and the
spread is reported so sampling noise is a measured quantity.""")
code("""import csv
def dock(receptor, pq, center, seed):
    out = pq.replace('.pdbqt', f'_out{seed}.pdbqt')
    subprocess.run(['./vina', '--receptor', receptor, '--ligand', pq,
                    '--center_x', str(center[0]), '--center_y', str(center[1]),
                    '--center_z', str(center[2]),
                    '--size_x', str(BOX), '--size_y', str(BOX), '--size_z', str(BOX),
                    '--exhaustiveness', str(EXHAUSTIVENESS), '--num_modes', '3', '--cpu', '2',
                    '--seed', str(seed), '--out', out],
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
            if len(row) == 4:
                done[(row[0], int(row[1]))] = (float(row[2]), int(row[3]))
    w = open(ckpt, 'a', newline='')
    todo = [(n, sd) for n in ligs for sd in SEEDS if (n, sd) not in done]
    for n, sd in tqdm(todo, desc=f"dock arm {r['arm']}"):
        pq, lab = ligs[n]
        v = dock(r['file'], pq, r['center'], sd)
        if v is not None:
            done[(n, sd)] = (v, lab)
            csv.writer(w).writerow([n, sd, v, lab]); w.flush()
    w.close()
    r['raw'] = done
    print(f"arm {r['arm']}: {len(done)} of {len(ligs)*len(SEEDS)} (ligand, seed) runs -> {ckpt}")""")

md("""## 6. Enrichment, with uncertainty and a stratified read

Three numbers per arm. The **stratified AUC** is the one to trust: it compares each active only
against its own property-matched decoys, so it cannot be skewed by the decoy set containing more
large molecules than the active set.""")
code("""import numpy as np, matplotlib.pyplot as plt, statistics
from sklearn.metrics import roc_auc_score, roc_curve
rng = np.random.default_rng(0)

def auc_of(a, d):
    a = np.asarray(a); d = np.asarray(d)
    gt = (a[:, None] > d[None, :]).sum(); eq = (a[:, None] == d[None, :]).sum()
    return (gt + 0.5 * eq) / (len(a) * len(d))

plt.figure(figsize=(5, 5))
plt.plot([0, 1], [0, 1], '--', c='grey', label='random (0.50)')
for r in RECEPTORS:
    mean_s, spread = {}, {}
    for n in ligs:
        vals = [r['raw'][(n, sd)][0] for sd in SEEDS if (n, sd) in r['raw']]
        if vals:
            mean_s[n] = statistics.mean(vals)
            spread[n] = statistics.pstdev(vals) if len(vals) > 1 else 0.0
    names = list(mean_s)
    y = np.array([1 if n in ACTIVES else 0 for n in names])
    score = -np.array([mean_s[n] for n in names])
    a, d = score[y == 1], score[y == 0]
    auc = float(roc_auc_score(y, score))
    boots = np.array([auc_of(rng.choice(a, len(a)), rng.choice(d, len(d))) for _ in range(20000)])
    lo, hi = (float(v) for v in np.percentile(boots, [2.5, 97.5]))
    try:
        from scipy.stats import mannwhitneyu
        p = float(mannwhitneyu(a, d, alternative='two-sided').pvalue)
    except Exception:
        allv = np.concatenate([a, d]); na = len(a)
        perm = np.array([auc_of(x[:na], x[na:]) for x in (rng.permutation(allv) for _ in range(20000))])
        p = float(np.mean(np.abs(perm - 0.5) >= abs(auc - 0.5)))
    # stratified: each active against ITS OWN decoys only
    locals_ = []
    for an in ACTIVES:
        if an not in mean_s:
            continue
        ds = [mean_s[k] for k in mean_s if k.startswith(f'decoy_{an}_')]
        if not ds:
            continue
        sa = mean_s[an]
        wins = sum(1 for v in ds if sa < v) + 0.5 * sum(1 for v in ds if sa == v)
        locals_.append((an, wins / len(ds), len(ds)))
    strat = statistics.mean([l for _, l, _ in locals_]) if locals_ else float('nan')
    noise = statistics.mean(list(spread.values())) if spread else 0.0
    r['stats'] = {'auc': round(auc, 3), 'ci95': [round(lo, 3), round(hi, 3)], 'p': round(p, 4),
                  'stratified_auc': round(strat, 3),
                  'per_active_stratified': {n: round(v, 3) for n, v, _ in locals_},
                  'mean_seed_sd': round(noise, 3),
                  'n_actives': int(y.sum()), 'n_decoys': int((1 - y).sum())}
    r['scores_mean'] = {n: round(v, 2) for n, v in mean_s.items()}
    r['scores_sd'] = {n: round(v, 2) for n, v in spread.items()}
    fpr, tpr, _ = roc_curve(y, score)
    r['roc'] = [[round(float(x), 4), round(float(t), 4)] for x, t in zip(fpr, tpr)]
    plt.plot(fpr, tpr, label=f"arm {r['arm']}: AUC {auc:.2f}")
    print(f"arm {r['arm']:5s} ({r['label']})")
    print(f"   pooled AUC      {auc:.3f}   95% CI {lo:.2f}-{hi:.2f}   p={p:.4f}")
    print(f"   STRATIFIED AUC  {strat:.3f}   <- the number to trust")
    print(f"   mean seed-to-seed SD {noise:.3f} kcal/mol  ({len(SEEDS)} seeds)")
    for n, v, k in locals_:
        print(f"      {n:30s} beats {v*k:4.1f}/{k:2d} of its own decoys  -> {v:.3f}")
plt.xlabel('false positive rate'); plt.ylabel('true positive rate')
plt.title('Dengue NS5 enrichment, Mg2+ retained vs stripped'); plt.legend(); plt.show()""")

md("## 7. Result, copy the printed JSON below")
code("""res = {
    'target': 'DENV_NS5',
    'method': 'retrospective enrichment, balanced property-matched decoys, 3 seeds',
    'comparison': 'catalytic Mg2+ retained vs stripped, same receptor and box',
    'box_size': BOX, 'exhaustiveness': EXHAUSTIVENESS, 'seeds': SEEDS,
    'decoys_per_active': DECOYS_PER_ACTIVE,
    'pool_mw_window': [POOL_MW_MIN, POOL_MW_MAX],
    'ligand_prep': 'phosphate/carboxylate deprotonated, EEM charges (formal charge preserved)',
    'arms': [{'arm': r['arm'], 'label': r['label'], 'center': r['center'],
              'receptor_atoms': r['n_atoms'], 'mg_atoms': r['n_metals'],
              'stats': r['stats'], 'roc': r['roc'],
              'scores_mean': r['scores_mean'], 'scores_sd': r['scores_sd']}
             for r in RECEPTORS],
}
RESULT = os.path.join(WORKDIR, 'ns5_mg_benchmark_result.json')
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
