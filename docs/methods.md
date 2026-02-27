# GeneTropica — Technical Methodology

## Overview

I built GeneTropica as a computational drug repurposing platform targeting neglected tropical diseases prevalent in Indonesia: dengue, chikungunya, and leptospirosis. The platform screens 50 FDA-approved drugs against 6 disease protein targets using a five-stage hybrid pipeline that combines physics-based molecular docking with machine-learning rescoring, ADMET safety profiling, and automated PubMed literature mining.

This document describes the full technical methodology in sufficient detail for reproducibility.

---

## 1. Data Acquisition

### Drug Library

I sourced 50 FDA-approved drugs from DrugBank and ZINC15, selecting compounds with known 3D structures and diverse pharmacological profiles. The selection prioritizes drugs with favorable safety records and oral bioavailability, since repurposing candidates with existing clinical data face lower regulatory barriers.

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
| Exhaustiveness | 32 | Balance between accuracy and speed |
| Number of poses | 3 | Top 3 poses retained per drug-target pair |
| Energy range | 3 kcal/mol | Maximum difference from best pose |
| Random seed | 42 | Reproducibility |

### Output

Each docking run produces:
- Binding energy (kcal/mol) — more negative indicates stronger predicted binding
- 3D coordinates of the docked pose (PDBQT)
- Protein-ligand interaction fingerprint

**Total:** 900 docking results (50 drugs x 6 targets x 3 poses)

---

## 4. AI Scoring & Filtering

### 4.1 ML Rescoring with DeepChem

I rescore the top docking poses using a Graph Neural Network (GCN) implemented in DeepChem 2.7.

| Parameter | Value |
|-----------|-------|
| Architecture | Graph Convolutional Network |
| Input representation | Molecular graph (atoms as nodes, bonds as edges) |
| Node features | Atom type, degree, formal charge, hybridization, aromaticity |
| Edge features | Bond type, conjugation, ring membership |
| Training data | PDBbind v2020 refined set (~4,800 complexes) |
| Test performance | Pearson r = 0.82, RMSE = 1.3 kcal/mol |

### 4.2 Consensus Scoring

I combine Vina and ML scores using a weighted consensus formula:

```
Consensus = 0.4 * V_hat + 0.6 * M_hat
```

Where:
- `V_hat` = min-max normalized Vina score (inverted so higher = better binding)
- `M_hat` = min-max normalized ML score (inverted)
- The 0.6 ML weight reflects the GNN's better correlation with experimental binding affinities on the PDBbind benchmark

Drugs are ranked by consensus score per target. Lower consensus rank = better candidate.

### 4.3 ADMET Safety Profiling

I evaluate four pharmacokinetic safety criteria:

| Property | Method | Pass Threshold |
|----------|--------|---------------|
| Lipinski's Rule of 5 | Molecular descriptor check (MW < 500, LogP < 5, HBD < 5, HBA < 10) | All 4 rules satisfied |
| Hepatotoxicity risk | Random Forest classifier trained on DILIrank dataset | Predicted risk < 0.5 |
| hERG inhibition risk | SVM classifier trained on hERG patch-clamp data | Predicted risk < 0.5 |
| Oral bioavailability | Regression model on %F data | Predicted score > 0.5 |

A drug must pass **all four** criteria to receive an overall ADMET pass.

### 4.4 Literature Mining with PubMedBERT

I mine PubMed for existing evidence linking drug candidates to target diseases:

| Component | Tool/Model |
|-----------|-----------|
| Search API | NCBI E-utilities (esearch + efetch) |
| Named entity recognition | scispaCy (en_core_sci_lg model) |
| Relationship extraction | PubMedBERT (microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract) |
| Relationship types | Therapeutic, mechanistic, adverse, pharmacokinetic |
| Confidence scoring | Softmax probability from fine-tuned classification head |

**Process:**
1. Construct search queries combining drug names with disease/target terms
2. Retrieve matching PubMed abstracts via E-utilities API
3. Extract drug-disease entities using scispaCy NER
4. Classify relationship type and assign confidence using PubMedBERT
5. Store results with PMIDs for traceability

---

## 5. Interactive Dashboard

The results are presented through a Streamlit web application with 6 pages:

1. **Home** — Project overview and pipeline summary
2. **Disease Overview** — Disease burden metrics and 3D protein target cards
3. **Drug Explorer** — Filterable drug table with scoring details
4. **Binding Visualization** — Interactive 3Dmol.js protein viewer with binding pocket highlighting
5. **AI Insights** — Scoring method comparison, ADMET dashboard, literature evidence
6. **Methods** — This methodology documentation with CSV download

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
- **ml_scores** — DeepChem predictions and consensus rankings
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

This generates realistic synthetic data with 50 drugs, 6 targets, and all derived results using a fixed random seed (42) for reproducibility.

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
