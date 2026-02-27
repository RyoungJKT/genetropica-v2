# GeneTropica

A computational drug repurposing platform I built to identify existing FDA-approved drugs that may be effective against neglected tropical diseases prevalent in Indonesia — primarily dengue, chikungunya, and leptospirosis.

## Why This Project

Neglected tropical diseases affect millions of people across Southeast Asia, yet drug development for these conditions is severely underfunded. Drug repurposing offers a faster, cheaper path: instead of developing new molecules from scratch, I screen thousands of existing FDA-approved drugs against disease protein targets to find new therapeutic uses.

## How It Works

GeneTropica implements a five-stage hybrid pipeline:

1. **Data Acquisition** — Gather FDA-approved drug structures from DrugBank/ZINC15 and disease protein targets from RCSB PDB
2. **AI Structure Prediction** — Predict 3D protein structures using ESMFold/ColabFold where crystal structures are unavailable
3. **Molecular Docking** — Physics-based binding simulation with AutoDock Vina
4. **AI Scoring & Filtering** — ML rescoring with DeepChem, ADMET toxicity prediction, PubMed NLP literature mining
5. **Interactive Dashboard** — Streamlit web app with 3D molecular visualization, drug rankings, and supporting evidence

## Target Diseases

| Disease | Protein Targets | Priority |
|---|---|---|
| Dengue | NS3 Protease-Helicase, NS5 RdRp, Envelope Protein | Primary |
| Chikungunya | nsP2 Protease, nsP1 Capping Enzyme | Secondary |
| Leptospirosis | LipL32 | Stretch Goal |

## Tech Stack

- **Language**: Python 3.11
- **Docking**: AutoDock Vina, Open Babel
- **ML/AI**: DeepChem, RDKit, PubMedBERT (transformers), scispaCy
- **Bioinformatics**: Biopython, ESMFold
- **Dashboard**: Streamlit, Plotly, Py3Dmol
- **Database**: SQLite
- **Deployment**: Streamlit Community Cloud (Docker-ready for AWS migration)

## Setup

### Option 1: Conda (recommended for local development)

```bash
# Clone the repository
git clone https://github.com/RyoungJKT/genetropica-v2.git
cd genetropica-v2

# Create conda environment
conda env create -f environment.yml
conda activate genetropica

# Initialize the database
python -c "from src.utils.db import init_db; init_db()"

# Run the dashboard
streamlit run app/app.py
```

### Option 2: Docker

```bash
docker-compose up --build
```

The dashboard will be available at `http://localhost:8501`.

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
│   └── components/         # Reusable UI components
├── src/                    # Core pipeline
│   ├── data_acquisition/   # Drug & target data fetchers
│   ├── structure_prediction/  # ESMFold/ColabFold wrappers
│   ├── docking/            # AutoDock Vina pipeline
│   ├── ai_scoring/         # ML rescoring & ADMET
│   └── utils/              # Config, database, helpers
├── data/                   # Data storage (raw, processed, results)
├── notebooks/              # Jupyter exploration notebooks
├── tests/                  # Test suite
├── scripts/                # Setup and pipeline scripts
└── docs/                   # Documentation
```

## License

MIT License. See [LICENSE](LICENSE) for details.

## Author

Russell Young — [RyoungJKT](https://github.com/RyoungJKT)
