"""Global configuration for GeneTropica pipeline."""

import os
from pathlib import Path

# Base directories
BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
DATA_DIR: Path = BASE_DIR / "data"
RAW_DIR: Path = DATA_DIR / "raw"
PROCESSED_DIR: Path = DATA_DIR / "processed"
STRUCTURES_DIR: Path = DATA_DIR / "structures"
LIGANDS_DIR: Path = DATA_DIR / "ligands"
DOCKING_DIR: Path = DATA_DIR / "docking_results"
DB_PATH: Path = DATA_DIR / "database" / "genetropica.db"

# Demonstration-data toggle. The shipped repository does not include the
# populated database (it is gitignored), so a fresh clone has no data until
# the real pipeline is run or scripts/generate_mock_data.py seeds
# demonstration data. The published results were produced by the real
# pipeline (AutoDock Vina docking, ChEMBL-trained RandomForest, RDKit ADMET,
# PubMed search); this toggle only controls the demonstration fallback.
USE_MOCK_DATA: bool = os.environ.get("USE_MOCK_DATA", "true").lower() == "true"

# Protein targets for all three diseases
TARGET_PROTEINS: dict = {
    "DENV_NS3": {
        "name": "NS3 Protease-Helicase",
        "pdb_id": "2VBC",
        "disease": "Dengue",
        "uniprot_id": "P27909",
    },
    "DENV_NS5": {
        "name": "NS5 RNA-dependent RNA Polymerase",
        "pdb_id": "5CCV",
        "disease": "Dengue",
        "uniprot_id": "P27909",
    },
    "DENV_E": {
        "name": "Envelope (E) Protein",
        "pdb_id": "1OAN",
        "disease": "Dengue",
        "uniprot_id": "P09866",
    },
    "CHIKV_nsP2": {
        "name": "nsP2 Protease",
        "pdb_id": "3TRK",
        "disease": "Chikungunya",
        "uniprot_id": "Q8JUX6",
    },
    "CHIKV_nsP1": {
        "name": "nsP1 Capping Enzyme",
        "pdb_id": "6Z0V",
        "disease": "Chikungunya",
        "uniprot_id": "Q8JUX5",
    },
    "LEPTO_LipL32": {
        "name": "LipL32",
        "pdb_id": "3FRH",
        "disease": "Leptospirosis",
        "uniprot_id": "Q8F8G2",
    },
}

# Disease groupings for dashboard filtering
DISEASES: dict = {
    "Dengue": {
        "targets": ["DENV_NS3", "DENV_NS5", "DENV_E"],
        "priority": "Primary",
    },
    "Chikungunya": {
        "targets": ["CHIKV_nsP2", "CHIKV_nsP1"],
        "priority": "Secondary",
    },
    "Leptospirosis": {
        "targets": ["LEPTO_LipL32"],
        "priority": "Stretch Goal",
    },
}
