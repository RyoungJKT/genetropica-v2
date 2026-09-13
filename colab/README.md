# Colab — dengue NS5 retrospective enrichment benchmark

Does AutoDock Vina rank **known** NS5 polymerase inhibitors above look-alike molecules that are
not known to work? That is the only fair way to find out whether a docking score means anything
for this target before trusting it on untested drugs.

`ns5_receptor_benchmark.ipynb` answers that, and runs entirely on free Colab CPU.

## Design

8 published NS5 / RdRp inhibitors are hidden among property-matched decoys. Each decoy matches
an active on molecular weight, logP, hydrogen-bond donors and acceptors, rotatable bonds and
formal charge, while being topologically dissimilar (Morgan-fingerprint Tanimoto below 0.35).
Everything is docked and ranked. A method that works puts the real inhibitors near the top.

The same ligands are docked into **two independently prepared receptors**, so receptor choice is
the only variable:

| | Arm A | Arm B |
|---|---|---|
| structure | 5CCV, chain A | 4V0R |
| resolution | 3.60 A | 2.40 A |
| box centre | (-48.3, 35.4, 36.9) | (-11.3, 19.2, -7.8) |
| centred on | motif A D533 with motif C GDD | motif C GDD with the catalytic Mg |

Box size is 25 A and exhaustiveness is 8 in both arms, with a fixed seed.

## The box guard

Before any docking, the notebook verifies for each receptor that:

- the catalytic site actually falls **inside** the search box,
- the box contains a sensible amount of protein (at least 400 atoms), and
- the box centre is not sitting in open solvent (within 4 A of protein).

It raises and refuses to dock if any check fails. Docking into a region that does not contain the
catalytic machinery produces confident, meaningless scores, so this is checked rather than assumed.

## Run it

1. Download `ns5_receptor_benchmark.ipynb`, then in Colab use **File > Upload notebook**.
2. **Runtime > Run all.** No GPU needed; AutoDock Vina is CPU-only.
3. The notebook mounts Google Drive and expects the two receptor files in
   `MyDrive/genetropica_ns5_benchmark/receptors/`. Upload `5CCV_chainA.pdbqt` and
   `4V0R_chainA.pdbqt` there once. If they are missing, the notebook offers a direct upload
   instead. Nothing is fetched from a code host.
4. Docking takes roughly 2 to 4 hours for both arms. Progress is **checkpointed to Drive per
   arm**, so a runtime reset resumes instead of restarting.
5. The result is written to `ns5_receptor_benchmark_result.json` and also printed between COPY
   markers in the cell output, which is the reliable way to retrieve it.

## Reporting

Each arm reports ROC-AUC with a **bootstrap 95% interval** and a Mann-Whitney p-value against the
0.5 null, plus enrichment factors at 1, 5 and 10 percent.

An AUC from 8 actives is imprecise. Read the interval, not the point estimate, and treat a result
as meaningful only if the interval separates from random. Report whatever comes out, including if
it sits at or below random.

## Honest scope

- **NS5 only.** It is the one target here with protein-specific known actives. The others have
  whole-virus phenotypic data, which cannot support a docking enrichment benchmark.
- **8 actives is few.** This is a real limit on the precision of the estimate, not a detail.
- **A benchmark measures the method, not the drugs.** A poor AUC says the scoring cannot rank
  these inhibitors on this receptor. It says nothing about whether any individual drug works.

## Files

- `ns5_receptor_benchmark.ipynb` — the benchmark notebook.
- `_build_ns5_benchmark_nb.py` — regenerates it (`python3 colab/_build_ns5_benchmark_nb.py`);
  every code cell is syntax-checked at generation time.
- `5CCV_chainA.pdbqt` — prepared receptor, 5CCV chain A.
- `4V0R_chainA.pdbqt` — prepared receptor, 4V0R at 2.40 A.
- `ns5_ai_docking_validation.ipynb` and `_build_ai_nb.py` — a separate head-to-head of classical
  docking against AI co-folding (Boltz-2, OpenFold3). Needs a GPU runtime.
