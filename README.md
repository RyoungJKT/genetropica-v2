# GeneTropica

A computational drug repurposing platform I built to identify existing FDA-approved drugs that may be effective against neglected tropical diseases prevalent in Indonesia — primarily dengue, chikungunya, and leptospirosis.

## Why This Project

Neglected tropical diseases affect millions of people across Southeast Asia, yet drug development for these conditions is severely underfunded. Drug repurposing offers a faster, cheaper path: instead of developing new molecules from scratch, I screen existing FDA-approved drugs against disease protein targets to find new therapeutic uses.

## Screenshots

> Screenshots will be added after deployment.

| Page | Description |
|------|-------------|
| ![Home](docs/screenshots/home.png) | Landing page with pipeline summary |
| ![Disease Overview](docs/screenshots/disease_overview.png) | Disease burden metrics and 3D protein targets |
| ![Drug Explorer](docs/screenshots/drug_explorer.png) | Filterable drug candidate table with scores |
| ![Binding Viewer](docs/screenshots/binding_viewer.png) | Interactive 3D protein-drug visualization |
| ![AI Insights](docs/screenshots/ai_insights.png) | Scoring analysis and ADMET safety dashboard |
| ![Methods](docs/screenshots/methods.png) | Pipeline diagram and CSV downloads |

## Quick Start

```bash
# Clone the repository
git clone https://github.com/RyoungJKT/genetropica-v2.git
cd genetropica-v2

# Create conda environment and activate
conda env create -f environment.yml
conda activate genetropica

# Generate demonstration data
python scripts/generate_mock_data.py

# Launch the dashboard
streamlit run app/app.py
```

The dashboard will be available at `http://localhost:8501`.

## Pipeline Overview

GeneTropica implements a five-stage hybrid pipeline:

```
 1. Data Acquisition     Gather FDA-approved drug structures and protein targets
         |
 2. Structure Prediction Use ESMFold/ColabFold for targets without crystal structures
         |
 3. Molecular Docking    Physics-based binding simulation with AutoDock Vina
         |
 4. AI Scoring           ML rescoring (DeepChem GNN) + ADMET + PubMed NLP mining
         |
 5. Interactive Dashboard  Streamlit app with 3D visualization and ranked results
```

### Key numbers

- **50** FDA-approved drugs screened
- **6** protein targets across 3 diseases
- **900** docking results (3 poses per drug-target pair)
- **4** ADMET safety criteria evaluated per drug
- Consensus scoring: `0.4 x Vina + 0.6 x ML`

## Target Diseases

| Disease | Protein Targets | Priority |
|---|---|---|
| Dengue | NS3 Protease-Helicase, NS5 RdRp, Envelope Protein | Primary |
| Chikungunya | nsP2 Protease, nsP1 Capping Enzyme | Secondary |
| Leptospirosis | LipL32 | Stretch Goal |

## Results

The dashboard ranks drug candidates by consensus score for each target protein. Key findings include:

- **Top candidates** are identified per target based on combined Vina docking and DeepChem ML scores
- **ADMET-safe hits** are filtered to only include drugs passing all four safety criteria (Lipinski, hepatotoxicity, hERG, oral bioavailability)
- **Novel discovery candidates** — drugs with strong computational scores but zero prior literature for the target disease — represent potential new repurposing opportunities
- **Literature-validated candidates** have existing PubMed evidence supporting the drug-disease connection

Full results are downloadable as CSV from the Methods page of the dashboard.

## Tech Stack

- **Language**: Python 3.11
- **Docking**: AutoDock Vina 1.2.5, Open Babel 3.1
- **ML/AI**: DeepChem 2.7, RDKit, PubMedBERT (transformers), scispaCy
- **Bioinformatics**: Biopython, ESMFold
- **Dashboard**: Streamlit, Plotly, 3Dmol.js
- **Database**: SQLite
- **Deployment**: Streamlit Community Cloud (Docker-ready for AWS migration)

## Setup

### Option 1: Conda (recommended for local development)

```bash
git clone https://github.com/RyoungJKT/genetropica-v2.git
cd genetropica-v2

conda env create -f environment.yml
conda activate genetropica

python -c "from src.utils.db import init_db; init_db()"
streamlit run app/app.py
```

### Option 2: Docker

```bash
docker-compose up --build
```

### Option 3: Quick setup script

```bash
bash scripts/setup_environment.sh
```

## Project Structure

```
genetropica-v2/
├── app/                    # Streamlit dashboard
│   ├── app.py              # Main entry point
│   ├── pages/              # Multi-page dashboard views
│   │   ├── 01_disease_overview.py
│   │   ├── 02_drug_explorer.py
│   │   ├── 03_binding_viewer.py
│   │   ├── 04_ai_insights.py
│   │   └── 05_methods.py
│   └── components/         # Reusable UI components
│       ├── charts.py       # Plotly chart builders
│       ├── filters.py      # Sidebar filter components
│       └── mol_viewer.py   # 3Dmol.js protein viewer
├── src/                    # Core pipeline
│   ├── data_acquisition/   # Drug & target data fetchers
│   ├── structure_prediction/  # ESMFold/ColabFold wrappers
│   ├── docking/            # AutoDock Vina pipeline
│   ├── ai_scoring/         # ML rescoring & ADMET
│   └── utils/              # Config, database, helpers
├── data/                   # Data storage (raw, processed, results)
├── docs/                   # Documentation and methodology
├── notebooks/              # Jupyter exploration notebooks
├── tests/                  # Test suite
├── scripts/                # Setup and pipeline scripts
├── environment.yml         # Conda environment specification
├── requirements.txt        # Pip requirements
├── Dockerfile              # Docker deployment
└── docker-compose.yml      # Docker Compose config
```

## Documentation

- [Technical Methodology](docs/methods.md) — Full pipeline documentation suitable for a research paper appendix

## Citation

```
Russell Young (2026). GeneTropica: AI-Powered Drug Repurposing
for Neglected Tropical Diseases in Indonesia. British School Jakarta.
https://github.com/RyoungJKT/genetropica-v2
```

## License

MIT License. See [LICENSE](LICENSE) for details.

## Author

Russell Young — [RyoungJKT](https://github.com/RyoungJKT)
British School Jakarta
