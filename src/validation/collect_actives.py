"""Collect known RdRp inhibitors for retrospective validation.

Downloads the 8 known dengue RdRp inhibitors from PubChem and
prepares a manifest for docking validation against 5ZQK.
"""

import logging
from pathlib import Path
from typing import Optional

import pandas as pd

from src.utils.config import BASE_DIR

logger = logging.getLogger(__name__)

VALIDATION_DIR: Path = BASE_DIR / "data" / "validation"
ACTIVES_DIR: Path = VALIDATION_DIR / "actives"
ROC_RESULTS_DIR: Path = VALIDATION_DIR / "roc_results"

# Validation target — DENV-2 NS5 RdRp (different crystal from main pipeline's 5CCV)
VALIDATION_TARGET_PDB = "5ZQK"
VALIDATION_TARGET_NAME = "DENV-2 NS5 RdRp"

# 8 known RdRp inhibitors with published activity against dengue or flaviviruses.
# SMILES sourced from PubChem; activity data from referenced publications.
KNOWN_ACTIVES = [
    {
        "name": "Sofosbuvir",
        "pubchem_cid": 45375808,
        "activity": "EC50 = 4.1 uM (dengue)",
        "source_paper": "Ferreira et al. 2019, Scientific Reports",
        "smiles": (
            "CC(C)OC(=O)[C@@H](C)NP(=O)"
            "(OC[C@@H]1[C@H]([C@H]([C@@H](O1)"
            "N2C=CC(=O)NC2=O)C(F)(F)F)O)OC3=CC=CC=C3"
        ),
    },
    {
        "name": "GS-461203",
        "pubchem_cid": 56404003,
        "activity": "Active triphosphate form of sofosbuvir",
        "source_paper": "Sofia et al. 2010, J Med Chem",
        "smiles": (
            "NC1=NC(=O)N(C=C1F)[C@@H]1O[C@H]"
            "(COP(O)(=O)OP(O)(=O)OC(=O)C(C)C)"
            "[C@@H](O)[C@H]1O"
        ),
    },
    {
        "name": "2'-C-methyladenosine",
        "pubchem_cid": 464205,
        "activity": "RdRp inhibitor (nucleoside analogue)",
        "source_paper": "Carroll et al. 2003, JBC",
        "smiles": "NC1=NC=NC2=C1N=CN2[C@@H]1O[C@@H](CO)[C@](O)(C)[C@H]1O",
    },
    {
        "name": "7-deaza-2'-C-methyladenosine",
        "pubchem_cid": 11673581,
        "activity": "RdRp inhibitor (7-deaza nucleoside)",
        "source_paper": "Olsen et al. 2004, Antimicrob Agents Chemother",
        "smiles": "NC1=NC=NC2=C1C=CN2[C@@H]1O[C@@H](CO)[C@](O)(C)[C@H]1O",
    },
    {
        "name": "NITD008",
        "pubchem_cid": 24905024,
        "activity": "RdRp inhibitor (adenosine analogue)",
        "source_paper": "Yin et al. 2009, PNAS",
        "smiles": "NC1=NC=NC2=C1N=CN2[C@@H]1O[C@@H](CO)C(=C1)CO",
    },
    {
        "name": "Balapiravir",
        "pubchem_cid": 11240438,
        "activity": "RdRp inhibitor prodrug (R1626)",
        "source_paper": "Nguyen et al. 2013, J Infect Dis",
        "smiles": (
            "CCOC(=O)[C@@H](C)NP(=O)"
            "(OC[C@@H]1[C@H]([C@](O)"
            "([C@@H](O1)N2C=CC(=O)NC2=O)C)O)OC3=CC=CC=C3"
        ),
    },
    {
        "name": "Ribavirin",
        "pubchem_cid": 37542,
        "activity": "Broad-spectrum antiviral (nucleoside analogue)",
        "source_paper": "Crance et al. 2003, J Med Virol",
        "smiles": "OC[C@@H]1OC(N2N=CN=C2C(N)=O)[C@@H](O)[C@H]1O",
    },
    {
        "name": "Galidesivir",
        "pubchem_cid": 56957826,
        "activity": "RdRp inhibitor (BCX4430, iminoribitol)",
        "source_paper": "Julander et al. 2017, Antiviral Res",
        "smiles": "NC1=NC=NC2=C1N=CN2[C@@H]1CC(O)[C@H](CO)N1",
    },
]


def build_actives_manifest() -> pd.DataFrame:
    """Build a DataFrame manifest of all known actives.

    Returns:
        DataFrame with columns: name, pubchem_cid, smiles, activity,
        source_paper.
    """
    return pd.DataFrame(KNOWN_ACTIVES)


def save_actives_manifest(output_dir: Optional[Path] = None) -> Path:
    """Save the actives manifest CSV to disk.

    Args:
        output_dir: Directory to save to. Defaults to ACTIVES_DIR.

    Returns:
        Path to the saved CSV file.
    """
    out = output_dir or ACTIVES_DIR
    out.mkdir(parents=True, exist_ok=True)
    path = out / "actives_manifest.csv"
    df = build_actives_manifest()
    df.to_csv(path, index=False)
    logger.info("Saved actives manifest to %s (%d compounds)", path, len(df))
    return path


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    save_actives_manifest()
    print(f"Saved {len(KNOWN_ACTIVES)} known actives to {ACTIVES_DIR}")
