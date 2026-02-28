# Phase 14: Molecular Dynamics Simulation

## Three-Drug Mechanism Comparison on DENV NS5 RdRp (PDB 5CCV)

| Drug | Consensus Rank | Score | Mechanism | Category |
|------|---------------|-------|-----------|----------|
| Celecoxib | #1 | 0.6846 | COX-2 selective inhibitor | M: Arbovirus Activity |
| Methotrexate | #3 | 0.4930 | DHFR / host-directed | D: Host Directed |
| Dasabuvir | #17 | 0.3758 | Non-nucleoside RdRp inhibitor | B: Published Dengue |

**Protocol:** 50 ns all-atom MD per drug, AMBER99SB-ILDN + GAFF2 + TIP3P

---

## Quick Start (Russell's Checklist)

### Step 1: Gather the 8 input files

Copy all input files into one folder:

```bash
mkdir -p ~/Desktop/md_upload
cp data/md_simulation/celecoxib/input/protein_5CCV.pdb ~/Desktop/md_upload/
cp data/md_simulation/celecoxib/input/celecoxib_docked.mol2 ~/Desktop/md_upload/
cp data/md_simulation/methotrexate/input/methotrexate_docked.mol2 ~/Desktop/md_upload/
cp data/md_simulation/dasabuvir/input/dasabuvir_docked.mol2 ~/Desktop/md_upload/
cp data/md_simulation/mdp/*.mdp ~/Desktop/md_upload/
```

You should have:

| # | File | Description |
|---|------|-------------|
| 1 | protein_5CCV.pdb | Cleaned DENV NS5 RdRp protein structure |
| 2 | celecoxib_docked.mol2 | Celecoxib best docking pose (Vina -6.563) |
| 3 | methotrexate_docked.mol2 | Methotrexate best docking pose (Vina -6.827) |
| 4 | dasabuvir_docked.mol2 | Dasabuvir best docking pose (Vina -7.392) |
| 5 | em.mdp | Energy minimisation parameters |
| 6 | nvt.mdp | NVT equilibration (100 ps, 300 K) |
| 7 | npt.mdp | NPT equilibration (100 ps, 300 K, 1 bar) |
| 8 | md.mdp | Production MD (50 ns) |

### Step 2: Open Google Colab

1. Go to https://colab.research.google.com
2. File > Upload notebook
3. Select `notebooks/md_simulation_colab.ipynb`

### Step 3: Enable GPU

1. Runtime > Change runtime type
2. Select **T4 GPU**
3. Click Save

### Step 4: Run the notebook

1. Runtime > Run all
2. When the upload dialog appears (Cell 2): **select ALL 8 files** from `~/Desktop/md_upload/`
3. The notebook will run each drug sequentially

### Step 5: Monitor progress

| Plot | Good Sign | Bad Sign |
|------|-----------|----------|
| Energy minimisation | Drops steeply, flattens | Flat or goes up |
| NVT temperature | Oscillates around 300 K | Stays at 0 or >1000 |
| NPT density | Stabilises near 1000 kg/m3 | Way off |
| Equilibration RMSD | Rises then levels off < 5 A | Shoots to 10+ |

### Step 6: Download results

After each drug completes, download the tar.gz package:
- `md_results_celecoxib.tar.gz`
- `md_results_methotrexate.tar.gz`
- `md_results_dasabuvir.tar.gz`

### Step 7: Extract to local project

```bash
cd genetropica-v2

mkdir -p data/md_simulation/celecoxib/trajectory
mkdir -p data/md_simulation/methotrexate/trajectory
mkdir -p data/md_simulation/dasabuvir/trajectory

cd data/md_simulation/celecoxib/trajectory
tar -xzf ~/Downloads/md_results_celecoxib.tar.gz

cd ../../methotrexate/trajectory
tar -xzf ~/Downloads/md_results_methotrexate.tar.gz

cd ../../dasabuvir/trajectory
tar -xzf ~/Downloads/md_results_dasabuvir.tar.gz
```

### Step 8: Verify (15 files total)

Each drug folder needs 5 key files:

| File | Description |
|------|-------------|
| md.xtc | Compressed trajectory (~1-3 GB) |
| md.tpr | Run input (topology + parameters) |
| md.gro | Final coordinates |
| md.edr | Energy data |
| topol.top | System topology |

Once all 15 files (5 per drug) are in place, you are ready for Part 2 (analysis).

---

## Timeline

| Step | Who | Time |
|------|-----|------|
| Preparation (this was done) | Russell | ~1 hour |
| Upload + start Colab | Russell | ~10 min |
| Celecoxib 50 ns | Colab (T4) | 24-72 hours |
| Methotrexate 50 ns | Colab (T4) | 24-72 hours |
| Dasabuvir 50 ns | Colab (T4) | 24-72 hours |
| Download + extract | Russell | ~20 min |
| Analysis (Part 2) | Russell | ~3-5 hours |
| **Total** | | **5-12 days** |

---

## Colab Free Tier Strategy

Use **chunked mode** (5 x 10 ns per drug). Each chunk takes ~5-14 hours.

| Day | Task |
|-----|------|
| 1-2 | Celecoxib chunks 1-5. Download results. |
| 3-4 | Methotrexate chunks 1-5. Download results. |
| 5-7 | Dasabuvir chunks 1-5. Download results. |

**Download each drug's results before starting the next!**

If disconnected: Re-open notebook > Cell 1 (reinstall) > Cell 16 (recovery).

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Colab disconnects | Use chunked mode. Re-run from recovery cell (Cell 16) |
| No GPU available | Try early morning UTC. Or Colab Pro ($10/month) |
| ACPYPE atom type error | Try `charge_method=gas` in Cell 4 |
| Box too small error | Change `-d 1.2` to `-d 1.5` in prepare_system |
| LINCS warning | EM may have converged poorly. Check em_energy plot |
| Download fails | Use Google Drive backup (uncomment Cell 5) |

---

## Directory Structure

```
data/md_simulation/
    celecoxib/
        input/          protein_5CCV.pdb + celecoxib_docked.mol2
        trajectory/     (after Colab: md.xtc, md.tpr, md.gro, md.edr, topol.top)
        analysis/       (Part 2: RMSD, H-bonds, MM-PBSA)
        mmpbsa/         (Part 2: binding free energy)
    methotrexate/
        input/          protein_5CCV.pdb + methotrexate_docked.mol2
        trajectory/     ...
        analysis/       ...
        mmpbsa/         ...
    dasabuvir/
        input/          protein_5CCV.pdb + dasabuvir_docked.mol2
        trajectory/     ...
        analysis/       ...
        mmpbsa/         ...
    comparison/         (Part 2: 3-drug mechanism comparison)
    mdp/                em.mdp, nvt.mdp, npt.mdp, md.mdp
    README.md           This file
notebooks/
    md_simulation_colab.ipynb
```

---

Russell Young — British School Jakarta
