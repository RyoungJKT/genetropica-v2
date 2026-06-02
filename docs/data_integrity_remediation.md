# GeneTropica — Data Integrity Remediation

**Source:** external scientific review of the dashboard data export (`GENETROPICA_DATA_INTEGRITY_FIXES.md`).
**Started:** 2026-06-02. Canonical repo: `/Users/darwin/Developer/genetropica-v2`.

## Ground rules (honored throughout)
1. No fabrication: unresolved or failing values are flagged, never filled with a plausible number.
2. Preserve honesty: the dengue NS5 retrospective docking AUC (~0.37, below random) is a feature, not a bug. It is not improved, hidden, re-weighted, or masked. If re-docking with corrected structures legitimately changes it, the new value is reported as-is.
3. One canonical structure source: every module reads each drug's structure from a single record.
4. Counts and metrics computed from data at runtime, not hardcoded.
5. Regression tests (`pytest`) ship with FIX-1, FIX-3, FIX-4, FIX-6.
6. Reproducible: scripts pinned, external lookups logged with source + fetch date.

## Decisions (confirmed with the project owner)
- **FIX-8:** reword to "complementary, partially overlapping" signals (keep the model; do not retrain).
- **Network use:** approved (PubChem for FIX-1, NCBI E-utilities for FIX-10).
- **Sequencing:** P0 first, then the rest in order, no review gate after P0.
- **Re-docking:** the corrected drugs are re-docked (full correctness), not just re-measured.

## Step 0 — pipeline inventory
- **Structures (SMILES):** were a hardcoded curated list in `src/data_acquisition/fetch_drugs.py` plus a second drug-add path; the second path produced truncated structures and some wrong PubChem CIDs. Canonical source is now the `drugs` table (rebuilt; see FIX-1).
- **Molecular weight / heavy atoms:** previously three paths (`drugs` table; `src/admet/descriptors.py` → `profiles.json`; `src/ai_scoring/admet_predict.py` → `admet` table). Being unified onto `drugs`.
- **Ligand efficiency / ranks:** `scripts/recompute_rankings.py` (LE = -Vina / heavy_atoms; drug-like band MW 250-600).
- **Docking:** `src/docking/run_vina.py` (Vina binary), receptors in `data/structures/*_clean.pdbqt`, grid in `docking_parameters`.
- **MD analysis:** was a Colab notebook (`notebooks/md_analysis_colab.ipynb`); raw trajectories present locally (`data/md_simulation/<drug>/results/.../md.xtc` + `.tpr`).
- **Literature:** `src/ai_scoring/literature_mining.py` (keyword PubMed) → `literature` table.
- **Interactions:** `src/docking/interaction_analysis.py` → `interactions` table (proximity-based classifier).
- **Reads:** `app/` pages + `scripts/export_dashboard_pdf.py` via `src/utils/db.py`.

## Per-fix status

| Fix | Verdict (vs code/data) | Status |
|-----|------------------------|--------|
| FIX-1 wrong MW/structures | Confirmed; 53 drugs had wrong MW (not 8). Root cause: truncated SMILES + wrong CIDs from a second add-path. | DONE (DB rebuilt from PubChem by verified name resolution; 100/100; criticals correct; no duplicate structures) |
| FIX-3 two MW sources | Confirmed (3 paths). | DONE (single canonical structure source; MW + heavy atoms recomputed with RDKit from it) |
| FIX-2 ligand efficiency | Confirmed, depends on FIX-1 + re-dock. | DONE (LE = -Vina / heavy_atoms recomputed; dual vina_rank + le_rank over the 250-600 band) |
| (re-dock) corrected drugs | 28 drug-like (250-600) re-docked vs 6 targets; 25 now out-of-band flagged, not ranked. | DONE (168 dockings, 0 failures; dasabuvir now NS5 #1) |
| FIX-4 MD RMSD/RMSF | Confirmed PBC/alignment artifact; trajectories on disk, re-analyzable. | DONE (NoJump + unwrap(protein) + align; protein RMSD 49 to ~2.8 Angstrom; ligand RMSD reported as n/a, min-distance used instead) |
| FIX-5 "GNN" label | Confirmed label bug; model is the ChEMBL RandomForest; validation scores are real (not synthetic). | DONE (relabelled "ML (RandomForest)" throughout the export) |
| FIX-6 drug counts | Confirmed (100 / 99 / 50). | DONE (counts computed at runtime) |
| FIX-7 6Z0V provenance | Confirmed (`predicted`; should be experimental cryo-EM). | DONE (provenance corrected) |
| FIX-8 independence | Confirmed (Vina is a feature). Decision: reword. | DONE (reworded to "complementary, partially overlapping"; model left unchanged per decision) |
| FIX-9 interaction types | Confirmed (neutral pibrentasvir shows 40 "Ionic"). | DONE (chemistry-aware classifier; pibrentasvir 0 ionic; 609 ionic/salt-bridge total across all drugs; export labels contacts as predicted and states the detection method) |
| FIX-10 PubMed verify | Confirmed (keyword, unverified). | DONE (NCBI esummary verify + evidence tiers; 12 PMID title mismatches and 103 weak/computational-tier links flagged; tiers shown in Appendix A) |
| FIX-11 chains/residues | Confirmed (chain "X" on nsP1, C/D/E/F on NS5). | DONE (chains/residues valid by construction post-FIX-9; NS5 catalytic Asp663/Asp664/Arg737 present in 5CCV; export states numbering follows the deposited PDB) |
| FIX-12 grid coords/poses | Partial: grid centers already exist in `docking_parameters`; publish + pose validity. | DONE (per-target grid center + box + exhaustiveness/modes published in the export methods section) |
| FIX-13 validation badges | Confirmed (no per-target field). | DONE (`targets.validation_status` set; only NS5 validated, AUC 0.37; export shows a per-target validation-status table) |

## FIX-1 result detail
- Rebuilt every drug from PubChem by **name** (stored CIDs were unreliable: e.g. pibrentasvir's CID pointed at a 430 Da compound). Stored per drug: canonical SMILES, InChIKey, source (PubChem), source CID, reference MW, fetch date. MW and heavy atoms recomputed with RDKit.
- Validation gate: RDKit MW within 1% of PubChem MW for all 100; no duplicate connectivity across distinct drugs; nothing auto-filled.
- 53 drugs changed structure. Split for docking: 28 still drug-like (re-docked); 21 now > 600 Da and 4 now < 250 Da fall outside the candidate band (flagged, not ranked). The former "top candidates" (velpatasvir, grazoprevir, pibrentasvir) were the oversized artifacts; removing them is the size-bias correction working as intended.
- Backup of the pre-fix DB: `data/database/genetropica.db.bak_pre_fix1`.

## Commit sequence
1. inventory + canonical structure source (FIX-1, FIX-3) + re-dock + regression tests.
2. recompute ligand efficiency and rankings (FIX-2); regenerate figures.
3. MD: unwrap + align before RMSD/RMSF (FIX-4); regenerate MD figures.
4. consistency: model name, drug counts, provenance, independence wording (FIX-5..8).
5. chemistry-aware interaction classification (FIX-9).
6. PubMed verification + tiering; chain/residue checks (FIX-10, FIX-11).
7. publish grid coords + prep logs; pose-validity checks (FIX-12).
8. per-target validation badges (FIX-13).
9. regression suite; regenerate figures and the PDF export.

## FIX-9 / 11 / 12 / 13 result detail (final batch)
- **FIX-9 interactions** (`scripts/reanalyze_interactions.py`): re-extracts contacts from the best docked pose (MODEL 1) with a chemistry-aware classifier. Ionic / salt-bridge is gated on the ligand actually carrying an ionizable group (SMARTS) of the charge opposite to the residue; SMARTS exclude amide, sulfonamide, phosphoramide, imine/nitrile, aromatic and anilino nitrogens so neutral ligands score zero ionic contacts. H-bond <= 3.5 A (polar N/O/S), hydrophobic <= 4.5 A (nonpolar C), pi-stacking <= 5.5 A (aromatic residue). Distances vectorised with `MDAnalysis.lib.distances.distance_array`. Result: 594 complexes, 6827 contacts, 609 ionic/salt-bridge total; pibrentasvir went from 40 spurious "Ionic" to 0.
- **FIX-11 chains/residues**: verified, not mutated. nsP1 carries chains A and X; NS5 carries C/D/E/F; the NS5 catalytic motif (Asp663, Asp664, Arg737) is present in 5CCV. Residue numbers and chain IDs in the export now state that they follow the deposited PDB for each target.
- **FIX-12 grid/poses**: all six targets already had grid centers in `docking_parameters`; these (center x/y/z, 25 A cubic box, exhaustiveness 8, 3 modes) are now published in the export methods section so every docking run is reproducible.
- **FIX-13 validation**: `targets.validation_status` is the single source. Only DENV_NS5 is retrospectively validated (docking AUC 0.37, below random); the other five read "not yet retrospectively validated; rankings are hypothesis-generating only". The export renders this as a per-target validation-status table.

## Completion (2026-06-02)
All 13 fixes plus the re-dock are DONE. 265 pytest tests pass. The professor-facing PDF (`~/Downloads/GeneTropica_Dashboard_Data_Export_<date>.pdf`, 45 pages) now surfaces: per-target validation badges, predicted-contact labelling with the detection method and PDB numbering note, the per-target docking grid, and per-link literature evidence tiers with PMID verification. The headline scientific change from the remediation: removing molecular-size bias dropped the oversized HCV direct-acting antivirals out of the NS5 top ranks (dasabuvir is now NS5 #1), and the NS5 AUC 0.37 honest-failure result is preserved throughout.
