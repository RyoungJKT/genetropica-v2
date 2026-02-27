"""ADMET profile orchestration: build, persist, and load full drug profiles."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from src.utils.config import BASE_DIR
from src.admet.descriptors import (
    compute_descriptors,
    check_lipinski,
    check_veber,
    check_ghose,
    check_egan,
    estimate_esol,
    check_pains,
    check_brenk,
)
from src.admet.boiled_egg import classify_absorption, classify_bbb

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

ADMET_DIR: Path = BASE_DIR / "data" / "admet"


# ---------------------------------------------------------------------------
# Single-drug profiling
# ---------------------------------------------------------------------------

def profile_drug(smiles: str) -> Optional[dict]:
    """Build a complete ADMET profile for a single SMILES string.

    Returns a dict with keys: descriptors, lipinski, veber, ghose, egan,
    esol, gi_absorption, bbb_permeant, pains_alerts, brenk_alerts,
    drug_likeness_score.  Returns None for invalid SMILES.
    """
    descriptors = compute_descriptors(smiles)
    if descriptors is None:
        return None

    lipinski = check_lipinski(descriptors)
    veber = check_veber(descriptors)
    ghose = check_ghose(descriptors)
    egan = check_egan(descriptors)
    esol = estimate_esol(descriptors)

    gi_absorption = classify_absorption(descriptors["tpsa"], descriptors["logp"])
    bbb_permeant = classify_bbb(descriptors["tpsa"], descriptors["logp"])

    pains_alerts = check_pains(smiles)
    brenk_alerts = check_brenk(smiles)

    # Drug-likeness score: count of passed criteria (0-5)
    drug_likeness_score = sum([
        lipinski["pass"],
        veber["pass"],
        ghose["pass"],
        egan["pass"],
        len(pains_alerts) == 0,
    ])

    return {
        "descriptors": descriptors,
        "lipinski": lipinski,
        "veber": veber,
        "ghose": ghose,
        "egan": egan,
        "esol": esol,
        "gi_absorption": gi_absorption,
        "bbb_permeant": bbb_permeant,
        "pains_alerts": pains_alerts,
        "brenk_alerts": brenk_alerts,
        "drug_likeness_score": drug_likeness_score,
    }


# ---------------------------------------------------------------------------
# Batch profiling from database
# ---------------------------------------------------------------------------

def profile_all_drugs(db_path: Optional[Path] = None) -> list[dict]:
    """Profile every drug in the database that has a SMILES string.

    Args:
        db_path: Optional path override for the SQLite database.

    Returns:
        A list of profile dicts, each augmented with drug_id, name, and smiles.
    """
    from src.utils.db import get_connection

    conn = get_connection(db_path)
    try:
        rows = conn.execute(
            "SELECT drug_id, name, smiles FROM drugs WHERE smiles IS NOT NULL"
        ).fetchall()
    finally:
        conn.close()

    profiles: list[dict] = []
    for row in rows:
        drug_id, name, smiles = row["drug_id"], row["name"], row["smiles"]
        result = profile_drug(smiles)
        if result is not None:
            profiles.append({
                "drug_id": drug_id,
                "name": name,
                "smiles": smiles,
                **result,
            })
    return profiles


# ---------------------------------------------------------------------------
# Persistence helpers
# ---------------------------------------------------------------------------

def save_profiles(profiles: list[dict], output_path: Optional[Path] = None) -> Path:
    """Save profile list to a JSON file.

    Args:
        profiles: List of profile dicts (as returned by profile_all_drugs).
        output_path: Destination path. Defaults to data/admet/profiles.json.

    Returns:
        The Path where the file was written.
    """
    path = Path(output_path) if output_path is not None else ADMET_DIR / "profiles.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as fh:
        json.dump(profiles, fh, indent=2, default=str)
    return path


def load_profiles(path: Optional[Path] = None) -> list[dict]:
    """Load profile list from a JSON file.

    Args:
        path: Source path. Defaults to data/admet/profiles.json.

    Returns:
        List of profile dicts.
    """
    path = Path(path) if path is not None else ADMET_DIR / "profiles.json"
    with open(path) as fh:
        return json.load(fh)
