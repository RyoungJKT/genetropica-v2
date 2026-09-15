#!/usr/bin/env python3
"""Generate colab/ns5_receptor_benchmark.ipynb.

A retrospective enrichment benchmark for dengue NS5. All 8 known RdRp inhibitors are hidden among
property-matched (DUD-E-style) decoys and ranked by AutoDock Vina score.

One receptor, one box, one seed: 4V0R (2.40 A) chain A with the catalytic Mg2+ retained.

What this run fixes, relative to the previous one:

  1. THE DECOY WINDOW. The previous run matched decoys on molecular weight +/- 25 and logP +/- 1.0
     against a 6000-molecule pool. Three actives (balapiravir, gs_461203, ribavirin) had only 2, 3
     and 3 eligible decoys at that setting, fell below the minimum, and were SILENTLY DROPPED. The
     benchmark then reported an AUC over 5 of 8 actives. The pool is now 20000 molecules and the
     window is +/- 40 Da and +/- 1.5 logP, which fills a full 10 decoys for every one of the 8.
  2. CHARGE-CONSISTENT MATCHING. Properties are now computed on the species that is actually
     docked, after deprotonation, so formal charge is matched on the docked state. Previously
     gs_461203 was matched as neutral and then docked at -2, against decoys docked at 0.
  3. NO SILENT EXCLUSION. If any active cannot be matched, the notebook stops and names it. A
     dropped active is what corrupted the previous result, so it can no longer happen quietly.
  4. ONE SEED. The previous run docked 3 seeds and measured the seed-to-seed spread at 0.05
     kcal/mol, far smaller than any difference of interest. That question is settled, so the extra
     seeds are dropped and the run is roughly 6x cheaper.
  5. ENRICHMENT FACTORS RESTORED. EF at 1, 5 and 10 percent is reported alongside AUC again.

Run: python3 colab/_build_ns5_benchmark_nb.py
"""
import json
from pathlib import Path

CELLS = []
def md(src): CELLS.append(("markdown", src))
def code(src): CELLS.append(("code", src))

md("""# Dengue NS5, retrospective enrichment benchmark

Does AutoDock Vina rank **known** NS5 polymerase inhibitors above look-alike molecules that are
not known to work? That is the only fair way to decide whether a docking score means anything for
this target before trusting it on untested drugs.

**Design.** All 8 published NS5 / RdRp inhibitors are hidden among property-matched decoys. Each
decoy matches its active on molecular weight, logP, hydrogen-bond donors and acceptors, rotatable
bonds and formal charge, while being topologically dissimilar (Morgan Tanimoto below 0.35). Every
active gets the same number of decoys, and no decoy is shared between actives. Everything is
docked and ranked. A method that works puts the real inhibitors near the top.

**Receptor.** 4V0R, 2.40 A, chain A, with the catalytic Mg2+ retained. Box centre
(-11.3, 19.2, -7.8), which is the motif C GDD centroid together with the metal. Box 25 A,
exhaustiveness 8, seed 42.

## What this run fixes

The previous version of this benchmark reported an AUC that was **computed over 5 of the 8
actives**. Three of them, balapiravir, gs_461203 and ribavirin, had only 2, 3 and 3 eligible
decoys under a molecular-weight window of +/- 25 Da against a 6000-molecule pool. They fell below
the per-active minimum and were dropped without the headline number saying so.

| | previous run | this run |
|---|---|---|
| decoy pool | 6000 | 20000 |
| MW / logP window | +/- 25 Da, +/- 1.0 | +/- 40 Da, +/- 1.5 |
| actives evaluated | **5 of 8** | **8 of 8** |
| decoys per active | 5, 5, 7, 10, 10 | 10 each |
| charge matched on | the neutral input | the **docked** species |
| behaviour if unmatchable | silently excluded | **stops and names it** |
| seeds | 3 | 1 |

Two further points on the changes:

- **Charge is now matched on what is actually docked.** Phosphate and carboxylate groups are
  deprotonated before docking, which takes gs_461203 to -2 while the other 7 stay neutral. The
  previous run matched decoys against the *neutral* input, so gs_461203 was docked at -2 against
  decoys docked at 0. Properties are now computed after deprotonation for actives and pool alike.
- **One seed is enough, and that is a measured claim.** The 3-seed run put the seed-to-seed
  standard deviation at 0.05 kcal/mol, an order of magnitude below any difference that would
  change a conclusion. So the extra seeds buy nothing and are dropped.

**Reporting.** ROC-AUC with a bootstrap 95% interval, a Mann-Whitney p-value against the 0.5 null,
enrichment factors at 1, 5 and 10 percent, and a **stratified AUC** in which every active is
compared only against its own matched decoys. The stratified number is the one to trust, because
it cannot be skewed by the decoy set happening to contain more large molecules than the active set.

**Power.** 8 actives is few, and that is a hard limit, not a detail. Dengue NS5 has only a handful
of published inhibitors, so an interval this wide is the best this target can support. Read the
interval, not the point estimate, and report whatever comes out, including a result at or below
random.

**Runtime.** Vina is CPU-only, no GPU. 88 ligands, one seed, so expect roughly 2 to 3 hours.
Progress is checkpointed to Drive, so a runtime reset resumes instead of restarting. Run via
**Runtime > Run all**.""")

code("""# Setup (~2 min): RDKit, scikit-learn, SciPy, AutoDock Vina binary (CPU).
!pip -q install rdkit scikit-learn scipy requests tqdm >/dev/null 2>&1
!apt-get -qq install -y openbabel >/dev/null 2>&1
import os, subprocess, json, math, time, hashlib, requests
if not os.path.exists('vina'):
    url = 'https://github.com/ccsb-scripps/AutoDock-Vina/releases/download/v1.2.5/vina_1.2.5_linux_x86_64'
    open('vina', 'wb').write(requests.get(url, timeout=180).content)
    os.chmod('vina', 0o755)
print('vina:', subprocess.run(['./vina', '--version'], capture_output=True, text=True).stdout.strip())""")

md("""## Google Drive

Checkpoints and results are saved here so a runtime reset does not lose progress. The receptor
file is read from here too, so this notebook does not depend on any code host.""")
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
code("""# One receptor: 4V0R chain A with the catalytic magnesium kept in place.
CENTER = [-11.3, 19.2, -7.8]          # motif C GDD centroid with the catalytic Mg
CATALYTIC = [[-13.0, 20.2, -5.5],     # GDD centroid, from the 4V0R deposition
             [-9.6, 18.2, -10.1]]     # catalytic Mg position
RECEPTOR = {'label': '4V0R 2.40 A chain A, catalytic Mg2+ retained',
            'filename': '4V0R_chainA_Mg.pdbqt',
            'center': CENTER, 'catalytic_points': CATALYTIC}

BOX               = 25      # A, cube side
EXHAUSTIVENESS    = 8       # kept at 8 so numbers stay comparable with the earlier runs
SEED              = 42      # one seed: the 3-seed run measured seed noise at 0.05 kcal/mol
DECOYS_PER_ACTIVE = 10      # exclusive, and every active gets the same number

# Decoy pool. 20000 (not 6000) because at 6000 three actives could not be matched at all.
POOL_MW_MIN       = 200
POOL_MW_MAX       = 600
DECOY_POOL_SIZE   = 20000
MIN_POOL          = 12000   # refuse to build decoys from a truncated ChEMBL pool

# Property-matching window, applied to the DEPROTONATED (as-docked) species.
# Widened from 25/1.0/1/2/2: at that setting balapiravir, gs_461203 and ribavirin had only
# 2, 3 and 3 eligible decoys in a 6000 pool and were silently dropped from the result.
MW_TOL, LOGP_TOL, HBD_TOL, HBA_TOL, ROT_TOL = 40, 1.5, 2, 3, 3
TANIMOTO_MAX      = 0.35    # a 'decoy' more similar than this is not a decoy
MIN_DECOYS_PER_ACTIVE = 8   # below this the run STOPS; actives are never dropped silently

MIN_ATOMS_IN_BOX  = 400     # box guard: a real pocket holds far more than this
MAX_CENTER_GAP    = 4.0     # box guard: a centre in a cavity is within a few A of protein
os.makedirs('lig', exist_ok=True)""")

md("""## Receptor

Upload `4V0R_chainA_Mg.pdbqt` to the `receptors` folder shown above, once. If it is missing, the
next cell offers a direct upload.""")
code("""RECEPTOR['file'] = os.path.join(RECEPTOR_DIR, RECEPTOR['filename'])
if not os.path.exists(RECEPTOR['file']):
    print('Not found in', RECEPTOR_DIR)
    print('   missing:', RECEPTOR['filename'])
    print('\\nUpload it now, or copy it into that Drive folder and re-run this cell.')
    try:
        from google.colab import files
        up = files.upload()
        for name, blob in up.items():
            open(os.path.join(RECEPTOR_DIR, name), 'wb').write(blob)
            print('saved to Drive:', name)
    except Exception as e:
        print('upload unavailable:', repr(e))

size = os.path.getsize(RECEPTOR['file']) if os.path.exists(RECEPTOR['file']) else 0
print(f"{RECEPTOR['filename']:24s} {size/1024:6.0f} KB  ({RECEPTOR['label']})")
if not size:
    raise SystemExit(f"Receptor missing: {RECEPTOR['file']}")""")

md("""## Box guard

Checks that the catalytic site falls inside the search box, that the box holds a sensible amount
of protein, that the centre is not in open solvent, and that the magnesium really is present. It
raises rather than docking if any check fails.

This guard exists because an earlier run of this project docked into a crystal-packing void: the
box was nowhere near the catalytic machinery, and Vina returned confident, meaningless scores.""")
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
atoms = read_pdbqt(RECEPTOR['file'])
cat_in = sum(1 for p in RECEPTOR['catalytic_points'] if inside(p, RECEPTOR['center'], half))
n_in = sum(1 for a in atoms if inside(a, RECEPTOR['center'], half))
nearest = min(math.dist(a[:3], RECEPTOR['center']) for a in atoms)
metals = [a for a in atoms if a[4] in ('Mg', 'MG')]
ok = (cat_in == len(RECEPTOR['catalytic_points']) and n_in >= MIN_ATOMS_IN_BOX
      and nearest <= MAX_CENTER_GAP and len(metals) >= 1)
RECEPTOR['n_atoms'] = len(atoms)
RECEPTOR['n_metals'] = len(metals)
print(f"{RECEPTOR['label']}: {len(atoms)} atoms")
print(f"   catalytic points inside box : {cat_in}/{len(RECEPTOR['catalytic_points'])}")
print(f"   atoms inside box            : {n_in}  (need >= {MIN_ATOMS_IN_BOX})")
print(f"   nearest atom to centre      : {nearest:.1f} A  (need <= {MAX_CENTER_GAP})")
print(f"   Mg atoms present            : {len(metals)}  (need >= 1)")
print(f"   VERDICT                     : {'PASS' if ok else 'FAIL'}")
if not ok:
    raise SystemExit('Box guard FAILED: refusing to dock.')""")

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
N_ACTIVES_INTENDED = len(ACTIVES)
print(N_ACTIVES_INTENDED, 'actives')""")

md("""## 2. Drug-like pool from ChEMBL (to draw decoys from)

Fetched once and **cached to Drive**, so a re-run loads the cache instead of calling ChEMBL again.
ChEMBL occasionally answers a burst with an HTML error page rather than JSON, so each request is
status-checked and retried with backoff. A short pool **stops** the run rather than quietly
yielding a thin decoy set.

The cache filename carries the pool size, so raising the size fetches afresh instead of loading a
smaller cached pool.""")
code("""from rdkit import Chem, RDLogger
RDLogger.DisableLog('rdApp.*')
POOL_CACHE = os.path.join(
    WORKDIR, f'chembl_pool_{POOL_MW_MIN}_{POOL_MW_MAX}_{DECOY_POOL_SIZE}.json')

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
        f'a truncated pool starves the hardest actives of decoys, which is exactly the bug this '
        f'run exists to fix. Delete {POOL_CACHE} and re-run.')
print('pool SMILES:', len(pool))""")

md("""## 3. Deprotonation, applied before anything is measured

Phosphate and carboxylic-acid groups are deprotonated; nothing else is touched. This matters for
matching as well as for docking: properties are measured on the species that is actually docked,
so formal charge is matched on the docked state.

A blanket pH filter is not used. On these molecules it strips sugar hydroxyls, which is wrong
chemistry, and it reported ribavirin at roughly -1.4 when ribavirin is neutral.""")
code("""ACID_PATTERNS = [Chem.MolFromSmarts('[$([OX2H1])]-[PX4]=[OX1]'),
                 Chem.MolFromSmarts('[CX3](=O)[OX2H1]')]

def deprotonate(smi_or_mol):
    \"\"\"Deprotonate phosphate/phosphonate and carboxylic acid OH only. Nothing else.\"\"\"
    m = Chem.MolFromSmiles(smi_or_mol) if isinstance(smi_or_mol, str) else smi_or_mol
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

print('charge of each active as it will be docked:')
for n, s in ACTIVES.items():
    print(f'   {n:30s} {Chem.GetFormalCharge(deprotonate(s)):+d}')
print('\\nOnly gs_461203, the active diphosphate species, carries charge. The sofosbuvir and')
print('balapiravir prodrugs are correctly neutral: their phosphorus is a phosphoramidate ester.')""")

md("""## 4. Balanced, charge-consistent, property-matched decoys

Every active gets the **same** number of decoys, and no decoy is shared between two actives.

Two things are done differently here. Actives are filled **scarcest first**, so a constrained
active claims its decoys before an easy one takes them; filling in dictionary order can starve a
hard active even when a full assignment exists. And if any active still cannot be filled, the run
**stops and names it**, because silently dropping actives is what invalidated the previous
result.""")
code("""from rdkit.Chem import Descriptors, rdMolDescriptors, AllChem, DataStructs
def feats(m):
    return dict(mw=Descriptors.MolWt(m), logp=Descriptors.MolLogP(m),
                hbd=rdMolDescriptors.CalcNumHBD(m), hba=rdMolDescriptors.CalcNumHBA(m),
                rot=rdMolDescriptors.CalcNumRotatableBonds(m), q=Chem.GetFormalCharge(m),
                fp=AllChem.GetMorganFingerprintAsBitVect(m, 2, 2048))

# Featurise the DEPROTONATED species, for actives and pool alike.
act = {n: feats(deprotonate(s)) for n, s in ACTIVES.items()}
act_fps = [a['fp'] for a in act.values()]
poolf = []
for s in pool:
    mm = deprotonate(s)
    if mm is not None:
        poolf.append((s, feats(mm)))
print('pool featurised:', len(poolf))

def matches(a, p):
    return (abs(a['mw'] - p['mw']) <= MW_TOL and abs(a['logp'] - p['logp']) <= LOGP_TOL
            and abs(a['hbd'] - p['hbd']) <= HBD_TOL and abs(a['hba'] - p['hba']) <= HBA_TOL
            and abs(a['rot'] - p['rot']) <= ROT_TOL and a['q'] == p['q'])

# Eligible candidates per active, before any are claimed.
cand = {}
for n, a in act.items():
    ids = [i for i, (s, p) in enumerate(poolf)
           if matches(a, p)
           and max(DataStructs.BulkTanimotoSimilarity(p['fp'], act_fps)) < TANIMOTO_MAX]
    cand[n] = ids
    print(f'   {n:30s} {len(ids):5d} eligible  (charge {a["q"]:+d})')

# Fill the scarcest active first so it is not starved by an easy one.
used, decoys, per_active = set(), {}, {}
for n in sorted(cand, key=lambda k: len(cand[k])):
    picked = [i for i in cand[n] if i not in used][:DECOYS_PER_ACTIVE]
    used.update(picked)
    per_active[n] = len(picked)
    for j, i in enumerate(picked):
        decoys[f'decoy_{n}_{j:02d}'] = poolf[i][0]

print('\\nassigned decoys per active:')
for n in ACTIVES:
    print(f'   {n:30s} {per_active[n]:3d}')
short = {n: c for n, c in per_active.items() if c < MIN_DECOYS_PER_ACTIVE}
if short:
    raise SystemExit(
        'Could not build a balanced decoy set. Too few matches for: '
        + ', '.join(f'{n} ({c})' for n, c in short.items())
        + f'\\nEvery active must reach {MIN_DECOYS_PER_ACTIVE} decoys. Widen the tolerances or '
          'raise DECOY_POOL_SIZE, then re-run. Actives are deliberately NOT dropped: an AUC '
          'computed over a subset of the actives is what invalidated the previous run.')
assert len(ACTIVES) == N_ACTIVES_INTENDED, 'actives must not be dropped'
print(f'\\nactives: {len(ACTIVES)}/{N_ACTIVES_INTENDED} | decoys: {len(decoys)} | '
      f'total ligands: {len(ACTIVES) + len(decoys)}')""")

md("""## 5. Ligand prep

The deprotonated molecule is embedded with ETKDGv3, relaxed with MMFF, and written to PDBQT with
**EEM** charges. EEM preserves formal charge. Gasteiger writes a net of zero even for an anion,
which would quietly discard the charge state that this run is trying to get right.""")
code("""def net_charge_in(pdbqt):
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
ligs, charged, failed = {}, [], []
for n, s in tqdm({**ACTIVES, **decoys}.items(), desc='prep'):
    pq, formal = prep(n, s)
    if pq:
        ligs[n] = (pq, 1 if n in ACTIVES else 0)
        if formal:
            charged.append((n, formal, round(net_charge_in(pq), 2)))
    else:
        failed.append(n)
print('prepared:', len(ligs), '|', sum(v[1] for v in ligs.values()), 'actives')
print('\\nligands carrying formal charge (name, formal, net charge written to pdbqt):')
for c in charged:
    print('   ', c)
missing_actives = [n for n in ACTIVES if n not in ligs]
if missing_actives:
    raise SystemExit(f'Ligand prep failed for actives: {missing_actives}. Refusing to continue.')
if failed:
    print('\\nprep failed for', len(failed), 'decoys (dropped, actives unaffected):', failed)""")

md("""## 6. Dock (checkpointed and resumable)

88 ligands, one seed each. The checkpoint filename carries a fingerprint of the exact ligand set,
so changing the decoy set starts a fresh checkpoint instead of silently reusing scores from an
older run in which the same decoy slot held a different molecule.""")
code("""import csv
LIGSET_ID = hashlib.sha1(
    json.dumps(sorted({**ACTIVES, **decoys}.items())).encode()).hexdigest()[:10]
print('ligand-set fingerprint:', LIGSET_ID)

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

ckpt = os.path.join(WORKDIR, f'scores_ns5_{LIGSET_ID}.csv')
done = {}
if os.path.exists(ckpt):
    for row in csv.reader(open(ckpt)):
        if len(row) == 3:
            done[row[0]] = (float(row[1]), int(row[2]))
    print(f'resuming: {len(done)} of {len(ligs)} already docked')
w = open(ckpt, 'a', newline='')
todo = [n for n in ligs if n not in done]
for n in tqdm(todo, desc='dock'):
    pq, lab = ligs[n]
    v = dock(RECEPTOR['file'], pq, RECEPTOR['center'], SEED)
    if v is not None:
        done[n] = (v, lab)
        csv.writer(w).writerow([n, v, lab]); w.flush()
w.close()
print(f'{len(done)} of {len(ligs)} ligands docked -> {ckpt}')
undocked_actives = [n for n in ACTIVES if n not in done]
if undocked_actives:
    raise SystemExit(f'Docking failed for actives: {undocked_actives}. Refusing to report.')""")

md("""## 7. Enrichment, with uncertainty, enrichment factors, and a stratified read

The **stratified AUC** is the one to trust: it compares each active only against its own
property-matched decoys, so it cannot be skewed by the decoy set containing more large molecules
than the active set.""")
code("""import numpy as np, matplotlib.pyplot as plt, statistics
from sklearn.metrics import roc_auc_score, roc_curve
rng = np.random.default_rng(0)

def auc_of(a, d):
    a = np.asarray(a); d = np.asarray(d)
    gt = (a[:, None] > d[None, :]).sum(); eq = (a[:, None] == d[None, :]).sum()
    return (gt + 0.5 * eq) / (len(a) * len(d))

scores = {n: v for n, (v, lab) in done.items()}
names = list(scores)
y = np.array([1 if n in ACTIVES else 0 for n in names])
score = -np.array([scores[n] for n in names])   # higher is better, Vina is more negative = better

auc = float(roc_auc_score(y, score))
a, d = score[y == 1], score[y == 0]
boots = np.array([auc_of(rng.choice(a, len(a)), rng.choice(d, len(d))) for _ in range(20000)])
lo, hi = (float(v) for v in np.percentile(boots, [2.5, 97.5]))
try:
    from scipy.stats import mannwhitneyu
    p = float(mannwhitneyu(a, d, alternative='two-sided').pvalue)
except Exception:
    allv = np.concatenate([a, d]); na = len(a)
    perm = np.array([auc_of(x[:na], x[na:]) for x in (rng.permutation(allv) for _ in range(20000))])
    p = float(np.mean(np.abs(perm - 0.5) >= abs(auc - 0.5)))

# Enrichment factor at 1, 5, 10 percent of the ranked list.
order = np.argsort(-score)
y_ranked = y[order]
ef = {}
for frac in (0.01, 0.05, 0.10):
    k = max(1, int(round(len(y) * frac)))
    hits = int(y_ranked[:k].sum())
    ef[f'{int(frac*100)}%'] = {'ef': round(float((hits / y.sum()) / frac), 2),
                               'actives_in_top_k': hits, 'k': k}

# Stratified: each active against ITS OWN decoys only.
locals_ = []
for an in ACTIVES:
    if an not in scores:
        continue
    ds = [scores[k] for k in scores if k.startswith(f'decoy_{an}_')]
    if not ds:
        continue
    sa = scores[an]
    wins = sum(1 for v in ds if sa < v) + 0.5 * sum(1 for v in ds if sa == v)
    locals_.append((an, wins / len(ds), len(ds)))
strat = statistics.mean([l for _, l, _ in locals_]) if locals_ else float('nan')

STATS = {'auc': round(auc, 3), 'ci95': [round(lo, 3), round(hi, 3)], 'p': round(p, 4),
         'stratified_auc': round(strat, 3),
         'per_active_stratified': {n: round(v, 3) for n, v, _ in locals_},
         'enrichment_factor': ef,
         'n_actives': int(y.sum()), 'n_decoys': int((1 - y).sum()),
         'decoys_per_active': per_active}

print(f"{RECEPTOR['label']}")
print(f"   pooled AUC      {auc:.3f}   95% CI {lo:.2f}-{hi:.2f}   p={p:.4f}")
print(f"   STRATIFIED AUC  {strat:.3f}   <- the number to trust")
print(f"   actives {int(y.sum())} of {N_ACTIVES_INTENDED}, decoys {int((1-y).sum())}")
for kk, vv in ef.items():
    print(f"   EF at {kk:4s}      {vv['ef']:5.2f}   ({vv['actives_in_top_k']} of "
          f"{int(y.sum())} actives in the top {vv['k']})")
print('\\n   each active against its own matched decoys:')
for n, v, k in locals_:
    print(f"      {n:30s} beats {v*k:4.1f}/{k:2d}  -> {v:.3f}")

fpr, tpr, _ = roc_curve(y, score)
ROC = [[round(float(x), 4), round(float(t), 4)] for x, t in zip(fpr, tpr)]
plt.figure(figsize=(5, 5))
plt.plot([0, 1], [0, 1], '--', c='grey', label='random (0.50)')
plt.plot(fpr, tpr, label=f'NS5, Mg2+ retained: AUC {auc:.2f}')
plt.xlabel('false positive rate'); plt.ylabel('true positive rate')
plt.title('Dengue NS5 retrospective enrichment'); plt.legend(); plt.show()""")

md("## 8. Result, copy the printed JSON below")
code("""res = {
    'target': 'DENV_NS5',
    'method': 'retrospective enrichment, balanced property-matched decoys, single seed',
    'receptor': RECEPTOR['label'],
    'receptor_file': RECEPTOR['filename'],
    'receptor_atoms': RECEPTOR['n_atoms'],
    'mg_atoms': RECEPTOR['n_metals'],
    'center': RECEPTOR['center'],
    'box_size': BOX,
    'exhaustiveness': EXHAUSTIVENESS,
    'seed': SEED,
    'seed_noise_kcal_prev_run': 0.05,
    'decoys_per_active': DECOYS_PER_ACTIVE,
    'pool_mw_window': [POOL_MW_MIN, POOL_MW_MAX],
    'pool_size': len(pool),
    'match_tolerances': {'mw': MW_TOL, 'logp': LOGP_TOL, 'hbd': HBD_TOL,
                         'hba': HBA_TOL, 'rot': ROT_TOL, 'tanimoto_max': TANIMOTO_MAX},
    'matched_on': 'deprotonated (as-docked) species, formal charge included',
    'ligand_prep': 'phosphate/carboxylate deprotonated, EEM charges (formal charge preserved)',
    'ligand_set_fingerprint': LIGSET_ID,
    'stats': STATS,
    'roc': ROC,
    'scores': {n: round(v, 2) for n, v in scores.items()},
}
RESULT = os.path.join(WORKDIR, 'ns5_enrichment_result.json')
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
