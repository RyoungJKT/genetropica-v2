# GeneTropica — Technical Methodology

## Overview

I built GeneTropica as a computational drug repurposing platform targeting neglected tropical diseases prevalent in Indonesia: dengue, chikungunya, and leptospirosis. The platform screens 100 FDA-approved drugs against 6 disease protein targets using a five-stage hybrid pipeline that combines physics-based molecular docking with a machine-learning activity prior, ADMET safety profiling, and automated PubMed literature search.

This document describes the full technical methodology in sufficient detail for reproducibility.

---

## 1. Data Acquisition

### Drug Library

I assembled a curated library of 100 FDA-approved drugs organized into 18 hypothesis-driven categories (positive controls, negative controls, and mechanism-based sets), with structures and properties from DrugBank and PubChem. The selection prioritizes drugs with favorable safety records and oral bioavailability, since repurposing candidates with existing clinical data face lower regulatory barriers.

**Processing steps:**
1. Download SDF/MOL2 3D conformers from ZINC15
2. Add hydrogens and assign Gasteiger partial charges using Open Babel 3.1
3. Convert to PDBQT format for AutoDock Vina compatibility
4. Extract molecular properties (MW, LogP, SMILES) from PubChem

### Protein Targets

I selected 6 protein targets across 3 diseases based on their role in pathogen survival and druggability:

| Target ID | Protein | Disease | PDB ID | UniProt |
|-----------|---------|---------|--------|---------|
| DENV_NS3 | NS3 Protease-Helicase | Dengue | 2VBC | P27909 |
| DENV_NS5 | NS5 RNA-dependent RNA Polymerase | Dengue | 5CCV | P27909 |
| DENV_E | Envelope (E) Protein | Dengue | 1OAN | P09866 |
| CHIKV_nsP2 | nsP2 Protease | Chikungunya | 3TRK | Q8JUX6 |
| CHIKV_nsP1 | nsP1 Capping Enzyme | Chikungunya | 6Z0V | Q8JUX5 |
| LEPTO_LipL32 | LipL32 | Leptospirosis | 3FRH | Q8F8G2 |

**Processing steps:**
1. Download experimental structures from RCSB PDB
2. Remove water molecules, ligands, and non-standard residues
3. Add polar hydrogens using AutoDockTools
4. Define binding site search boxes based on known active site residues
5. Convert to PDBQT format

---

## 2. Structure Prediction

For targets where experimental structures are unavailable or incomplete, I use ESMFold (Meta AI) for fast single-sequence structure prediction, with ColabFold (AlphaFold2 + MMseqs2) as a fallback for higher accuracy.

**Validation:** Predicted structures are aligned against known binding site residues to verify that the active site geometry is preserved. RMSD values below 2.0 A against homologous crystal structures are considered acceptable.

All 6 targets in the current dataset have experimental PDB structures, so structure prediction was not required for this iteration.

---

## 3. Molecular Docking

### Software and Parameters

I use AutoDock Vina 1.2.5 for molecular docking with the following parameters:

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Search box dimensions | 25 x 25 x 25 A | Covers entire binding pocket with margin |
| Box center | Known active site centroid | Derived from literature or co-crystal ligands |
| Exhaustiveness | 8 | AutoDock Vina default; adequate for screening |
| Number of poses | 3 | Top 3 poses retained per drug-target pair |
| Energy range | 3 kcal/mol | Maximum difference from best pose |
| Random seed | 42 | Reproducibility |

### Output

Each docking run produces:
- Binding energy (kcal/mol) — more negative indicates stronger predicted binding
- 3D coordinates of the docked pose (PDBQT)
- Protein-ligand interaction fingerprint

**Total:** ~1,780 docking poses (100 drugs x 6 targets, 3 poses each; 594 of 600 drug-target pairs completed, 6 auranofin runs failed on its gold atom)

---

## 4. AI Scoring & Filtering

### 4.1 ML Rescoring with a RandomForest classifier

I score each drug with a scikit-learn RandomForest classifier. (An earlier design attempted a DeepChem graph neural network, but with a small, target-specific dataset a RandomForest proved the more reliable and reproducible choice, so it is what ships.)

| Parameter | Value |
|-----------|-------|
| Model | RandomForest classifier (100 trees) |
| Input representation | 2048-bit Morgan fingerprint (radius 2) + normalized Vina score |
| Training data | 166 experimental binding measurements from ChEMBL (HCV NS5B, dengue NS5, influenza RdRp) |
| Cross-validation | AUC 0.875 +/- 0.094 (5-fold stratified) |
| Important limitation | Ligand-based and target-agnostic: a drug receives the same score for every target, so the ML score is used as a supporting activity prior, not a per-target binding prediction |

### 4.2 Ranking (dual-metric, bias-aware)

Docking-based scoring has well-documented biases, so I do not collapse everything into a single number. Raw AutoDock Vina favours larger molecules (a size bias); ligand efficiency (binding energy per heavy atom) corrects the size bias but over-rewards very small fragments; and the ML score above is target-agnostic. I therefore restrict candidate lists to a drug-like molecular-weight window (250-600 Da) and rank by BOTH raw Vina score and ligand efficiency, presented side by side.

Retrospective ROC validation (known actives vs property-matched decoys) showed docking discriminated well for most targets but poorly for dengue NS5 (AUC 0.37, below random), so for NS5 the mechanistic and literature evidence carry more weight than the docking score. A legacy weighted consensus (0.4 x Vina + 0.6 x ML) is retained in the database for reference but is intentionally not the headline ranking, because weighting the target-agnostic ML term heavily made one molecule top nearly every target.

### 4.3 ADMET Safety Profiling

I evaluate four pharmacokinetic safety criteria:

| Property | Method | Pass Threshold |
|----------|--------|---------------|
| Lipinski's Rule of 5 | Molecular descriptor check (MW < 500, LogP < 5, HBD < 5, HBA < 10) | All 4 rules satisfied |
| Hepatotoxicity flag | RDKit descriptors + structural-alert heuristics (PAINS/Brenk) | Low-risk flag |
| hERG / cardiac flag | RDKit descriptor heuristics | Low-risk flag |
| Oral bioavailability | Veber rules + BOILED-Egg absorption model (RDKit) | Pass |

A drug must pass **all four** criteria to receive an overall ADMET pass.

### 4.4 Literature Mining (automated PubMed search)

I mine PubMed for existing evidence linking drug candidates to target diseases using the NCBI E-utilities API with keyword and synonym matching. (A PubMedBERT/scispaCy NLP layer was scoped as an optional upgrade, but the shipped pipeline uses keyword matching.)

| Component | Tool/Method |
|-----------|-----------|
| Search API | NCBI E-utilities (esearch + efetch) |
| Matching | Drug-name and synonym keyword matching against disease/target terms |
| Output | PubMed entries stored with PMIDs for traceability |

**Process:**
1. Construct search queries combining drug names (and synonyms) with disease/target terms
2. Retrieve matching PubMed entries via the E-utilities API
3. Deduplicate and store results with PMIDs for traceability
4. Flag drug-target pairs with strong computational scores but no literature as candidate novel findings

---

## 5. Interactive Dashboard

The results are presented through a Streamlit web application with a Home landing page and 9 content pages:

1. **Disease Overview** — Disease burden metrics and 3D protein target cards
2. **Drug Explorer** — Filterable drug table with Vina and ligand-efficiency rankings
3. **Binding Visualization** — Interactive 3Dmol.js protein viewer with binding pocket highlighting
4. **AI Insights** — Scoring comparison, ADMET dashboard, literature evidence
5. **Methods** — This methodology documentation with CSV download
6. **Methodology Validation** — Retrospective ROC curves and enrichment factors
7. **Conservation** — Multiple sequence alignment and per-residue conservation
8. **ADMET Profiling** — Drug-likeness filters, BOILED-Egg, structural alerts
9. **MD Simulation** — 50 ns trajectory stability analysis for selected candidates

### Key Technologies

| Component | Technology |
|-----------|-----------|
| Web framework | Streamlit 1.38+ |
| Charts | Plotly 5.x |
| 3D viewer | 3Dmol.js (embedded via st.components.html) |
| Database | SQLite 3 |
| Deployment | Streamlit Community Cloud (Docker-ready for AWS) |

---

## 6. Database Schema

The SQLite database contains 7 tables:

- **drugs** — Drug library (drug_id, name, drugbank_id, indication, SMILES, MW, LogP)
- **targets** — Protein targets (target_id, name, disease, PDB ID, UniProt ID)
- **docking_results** — Vina scores and pose paths (drug_id, target_id, score, pose_rank)
- **ml_scores** — RandomForest activity prior, ligand efficiency, and per-target Vina/LE ranks
- **admet** — ADMET safety profiles per drug
- **literature** — PubMed references with relationship types and confidence
- **interactions** — Protein-ligand interaction fingerprints per docking pose

---

## 7. Reproducibility

### Environment

```bash
git clone https://github.com/RyoungJKT/genetropica-v2.git
cd genetropica-v2
conda env create -f environment.yml
conda activate genetropica
```

### Pipeline Execution

```bash
# Step 1: Data acquisition
python -m src.data_acquisition.fetch_drugs

# Step 2: Structure preparation
python -m src.structure_prediction.predict

# Step 3: Molecular docking
python -m src.docking.run_vina

# Step 4: AI scoring
python -m src.ai_scoring.rescore

# Step 5: Dashboard
streamlit run app/app.py
```

### Mock Data (for demonstration)

```bash
python scripts/generate_mock_data.py
```

This generates realistic synthetic data (100 drugs, 6 targets) for local UI testing using a fixed random seed (42). The headline results come from the real pipeline, not this demonstration data.

---

## Citation

```
Russell Young (2026). GeneTropica: AI-Powered Drug Repurposing
for Neglected Tropical Diseases in Indonesia. British School Jakarta.
https://github.com/RyoungJKT/genetropica-v2
```

---

## License

MIT License. See [LICENSE](../LICENSE) for details.
