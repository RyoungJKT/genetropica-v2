# Colab: dengue NS5 retrospective enrichment benchmark

Does AutoDock Vina rank **known** NS5 polymerase inhibitors above look-alike molecules that are
not known to work? That is the only fair way to find out whether a docking score means anything
for this target before trusting it on untested drugs.

`ns5_receptor_benchmark.ipynb` answers that, and runs entirely on free Colab CPU.

## Design

All 8 published NS5 / RdRp inhibitors are hidden among property-matched decoys. Each decoy matches
its active on molecular weight, logP, hydrogen-bond donors and acceptors, rotatable bonds and
formal charge, while being topologically dissimilar (Morgan Tanimoto below 0.35). Every active gets
10 decoys, no decoy is shared between two actives, and 88 ligands are docked and ranked. A method
that works puts the real inhibitors near the top.

| | |
|---|---|
| receptor | 4V0R, chain A, 2.40 A, catalytic Mg2+ retained |
| box centre | (-11.3, 19.2, -7.8), the motif C GDD centroid with the metal |
| box size | 25 A |
| exhaustiveness | 8 |
| seed | 42 (single) |
| decoy pool | 20000 ChEMBL molecules, MW 200 to 600 |
| matching window | MW +/- 40, logP +/- 1.5, HBD +/- 2, HBA +/- 3, rotatable +/- 3 |

## What the previous run got wrong

The earlier version of this benchmark reported an AUC that was **computed over 5 of the 8
actives**, and the headline number did not say so.

It matched decoys on MW +/- 25 and logP +/- 1.0 against a 6000-molecule pool. At that setting
balapiravir, gs_461203 and ribavirin had only 2, 3 and 3 eligible decoys, fell below the per-active
minimum, and were dropped. Enlarging the pool alone does not fix it: at the same tolerances against
20000 molecules those three still reach only 6, 4 and 5. The window itself had to widen.

Four changes follow from that:

1. **Pool 20000 and a wider window.** Every one of the 8 actives now fills a full 10 decoys.
2. **Charge matched on the docked species.** Phosphate and carboxylate groups are deprotonated
   before docking, which takes gs_461203 to -2 while the other 7 stay neutral. Properties are now
   measured *after* deprotonation for actives and pool alike, so a -2 active draws -2 decoys.
   Previously it was matched as neutral and then docked at -2 against decoys docked at 0.
3. **Actives are never dropped silently.** If an active cannot be matched the notebook stops and
   names it. That failure mode is what invalidated the previous result.
4. **One seed.** The 3-seed run measured the seed-to-seed spread at 0.05 kcal/mol, far below any
   difference that would change a conclusion, so the extra seeds are dropped. The run is about 6x
   cheaper as a result.

Two further safeguards: decoys are assigned **scarcest active first**, because filling in
dictionary order can starve a constrained active even when a full assignment exists; and the
checkpoint filename carries a fingerprint of the exact ligand set, so changing the decoy set starts
a fresh checkpoint instead of reusing scores from a run in which the same decoy slot held a
different molecule.

## The box guard

Before any docking, the notebook verifies that:

- the catalytic site actually falls **inside** the search box,
- the box contains a sensible amount of protein (at least 400 atoms),
- the box centre is not sitting in open solvent (within 4 A of protein), and
- the magnesium is really present.

It raises and refuses to dock if any check fails. This guard exists because an earlier run of this
project docked into a crystal-packing void: the box was nowhere near the catalytic machinery and
Vina returned confident, meaningless scores.

## Run it

1. Download `ns5_receptor_benchmark.ipynb`, then in Colab use **File > Upload notebook**.
2. **Runtime > Run all.** No GPU needed; AutoDock Vina is CPU-only.
3. The notebook mounts Google Drive and expects `4V0R_chainA_Mg.pdbqt` in
   `MyDrive/genetropica_ns5_benchmark/receptors/`. Upload it there once. If it is missing, the
   notebook offers a direct upload instead. Nothing is fetched from a code host.
4. Docking takes roughly 2 to 3 hours for 88 ligands. Progress is **checkpointed to Drive**, so a
   runtime reset resumes instead of restarting.
5. The result is written to `ns5_enrichment_result.json` and also printed between COPY markers in
   the cell output, which is the reliable way to retrieve it.

## Reporting

ROC-AUC with a **bootstrap 95% interval**, a Mann-Whitney p-value against the 0.5 null, enrichment
factors at 1, 5 and 10 percent, and a **stratified AUC** in which each active is compared only
against its own matched decoys. The stratified number is the one to trust, because it cannot be
skewed by the decoy set happening to contain more large molecules than the active set.

An AUC from 8 actives is imprecise. Read the interval, not the point estimate, and treat a result as
meaningful only if the interval separates from random. Report whatever comes out, including if it
sits at or below random.

## Honest scope

- **NS5 only.** It is the one target here with protein-specific known actives. The others have
  whole-virus phenotypic data, which cannot support a docking enrichment benchmark.
- **8 actives is few.** Dengue NS5 has only a handful of published inhibitors, so a wide interval is
  the best this target can support. This is a real limit on the precision of the estimate, not a
  detail, and no amount of re-running fixes it.
- **A benchmark measures the method, not the drugs.** A poor AUC says the scoring cannot rank these
  inhibitors on this receptor. It says nothing about whether any individual drug works.

## Files

- `ns5_receptor_benchmark.ipynb`: the benchmark notebook.
- `_build_ns5_benchmark_nb.py`: regenerates it (`python3 colab/_build_ns5_benchmark_nb.py`);
  every code cell is syntax-checked at generation time.
- `4V0R_chainA_Mg.pdbqt`: the receptor used by the benchmark, 4V0R chain A at 2.40 A with the
  catalytic magnesium retained.
- `4V0R_chainA.pdbqt`: the same structure with the metal stripped. Kept from the earlier
  metal-on/metal-off comparison; not used by the current notebook.
- `5CCV_chainA.pdbqt`: 5CCV chain A, from the earlier two-receptor comparison. Not used: at 3.60 A
  with no magnesium in the crystal it is the weaker of the two structures.
- `ns5_ai_docking_validation.ipynb` and `_build_ai_nb.py`: a separate head-to-head of classical
  docking against AI co-folding (Boltz-2, OpenFold3). Needs a GPU runtime. **Do not run it yet:**
  it still loads the 8-chain receptor and the void box centre that the box guard above was written
  to catch, so its numbers would be meaningless until that is fixed.
