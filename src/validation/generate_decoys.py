"""Generate property-matched decoys for ROC validation.

For each known active, generates topologically dissimilar but
property-matched decoy molecules using RDKit. Follows the DUD-E
methodology: match MW (+/-25%), LogP (+/-1.0), rotatable bonds (+/-2),
but require Tanimoto < 0.4 for structural dissimilarity.

Fallback approach when DUD-E web service is unavailable: enumerate
candidate molecules from a curated fragment library and filter by
property constraints.
"""

import logging
import random
from pathlib import Path
from typing import Optional

import pandas as pd
from rdkit import Chem
from rdkit.Chem import AllChem, Descriptors, DataStructs, rdMolDescriptors

from src.utils.config import BASE_DIR
from src.validation.collect_actives import KNOWN_ACTIVES

logger = logging.getLogger(__name__)

DECOYS_DIR: Path = BASE_DIR / "data" / "validation" / "decoys"

# Fragment library — diverse drug-like fragments for decoy generation.
# These represent common scaffolds found in FDA-approved drugs and
# ZINC drug-like subset, covering a broad MW and LogP range.
_FRAGMENT_LIBRARY = [
    # Small heterocycles (MW ~100-200)
    "c1ccncc1",          # pyridine
    "c1ccc2[nH]ccc2c1",  # indole
    "c1cnc2ccccc2n1",    # quinazoline
    "c1ccc2ncccc2c1",    # quinoline
    "C1CCNCC1",          # piperidine
    "C1CCOCC1",          # tetrahydropyran
    "C1CCNC1",           # pyrrolidine
    "c1cn[nH]c1",        # pyrazole
    "c1ccoc1",           # furan
    "c1ccsc1",           # thiophene
    "c1ccc(cc1)O",       # phenol
    "c1ccc(cc1)N",       # aniline
    "c1ccc(cc1)F",       # fluorobenzene
    "c1ncc[nH]1",        # imidazole
    "C1CC1N",            # cyclopropylamine
    "c1ccc2c(c1)cccc2",  # naphthalene
    # Medium fragments (MW ~150-300)
    "OC(=O)c1ccccc1",              # benzoic acid
    "NC(=O)c1ccncc1",              # nicotinamide
    "CC(=O)Nc1ccccc1",             # acetanilide
    "c1ccc(cc1)C(=O)O",            # benzoic acid (alt)
    "c1ccc(cc1)S(=O)(=O)N",        # benzenesulfonamide
    "OC(=O)CN1CCCC1",              # proline derivative
    "NC1=NC(=O)N(C=C1)C",          # cytosine derivative
    "OC1CC(O)C(O1)CO",             # ribose-like
    "c1ccc2c(c1)[nH]c(=O)[nH]2",  # benzimidazolone
    "CC(C)CC(=O)O",                # isovaleric acid
    "c1ccc(-c2ccccc2)cc1",         # biphenyl
    "C1CCC(CC1)NC(=O)C",           # cyclohexyl acetamide
    "OCC1OC(O)C(O)C1O",            # deoxyribose-like
    "c1ccc(cc1)OCC(=O)O",          # phenoxyacetic acid
]

# Functional group decorations to expand diversity
_DECORATIONS = [
    ("", ""),        # no change
    ("O", ""),       # add hydroxyl
    ("N", ""),       # add amine
    ("F", ""),       # add fluorine
    ("Cl", ""),      # add chlorine
    ("C(=O)O", ""),  # add carboxyl
    ("OC", ""),      # add methoxy
    ("C(=O)N", ""),  # add amide
    ("CC", ""),      # add ethyl
    ("C(C)C", ""),   # add isopropyl
]


def _compute_properties(mol: Chem.Mol) -> dict:
    """Compute drug-like properties for filtering."""
    return {
        "mw": Descriptors.MolWt(mol),
        "logp": Descriptors.MolLogP(mol),
        "rotatable_bonds": rdMolDescriptors.CalcNumRotatableBonds(mol),
        "hbd": rdMolDescriptors.CalcNumHBD(mol),
        "hba": rdMolDescriptors.CalcNumHBA(mol),
    }


def _fingerprint(mol: Chem.Mol):
    """Compute Morgan fingerprint for similarity calculation."""
    return AllChem.GetMorganFingerprintAsBitVect(mol, 2, nBits=2048)


def _enumerate_candidates(seed: int = 42) -> list[str]:
    """Enumerate candidate SMILES by combining fragments with decorations.

    Returns a list of unique, valid SMILES strings.
    """
    rng = random.Random(seed)
    candidates = set()

    for frag in _FRAGMENT_LIBRARY:
        mol = Chem.MolFromSmiles(frag)
        if mol is None:
            continue
        candidates.add(Chem.MolToSmiles(mol))

        # Try adding decorations at available positions
        for dec, _ in _DECORATIONS:
            if not dec:
                continue
            # Simple concatenation approach — attach decoration
            for connector in ["C", "CC", "CCC", "O", "N"]:
                trial = f"{frag}{connector}{dec}"
                trial_mol = Chem.MolFromSmiles(trial)
                if trial_mol is not None:
                    smi = Chem.MolToSmiles(trial_mol)
                    candidates.add(smi)

    # Also try combining two small fragments
    small_frags = [f for f in _FRAGMENT_LIBRARY[:10] if Chem.MolFromSmiles(f)]
    for i, f1 in enumerate(small_frags):
        for f2 in small_frags[i + 1:]:
            for linker in ["C", "CC", "CCC", "O", "NC(=O)"]:
                trial = f"{f1}{linker}{f2}"
                trial_mol = Chem.MolFromSmiles(trial)
                if trial_mol is not None:
                    smi = Chem.MolToSmiles(trial_mol)
                    candidates.add(smi)

    result = list(candidates)
    rng.shuffle(result)
    return result


def generate_decoys_for_active(
    active_smiles: str,
    n_decoys: int = 30,
    seed: int = 42,
    mw_tolerance: float = 0.25,
    logp_tolerance: float = 1.0,
    rotbond_tolerance: int = 2,
    max_tanimoto: float = 0.4,
) -> list[str]:
    """Generate property-matched, topologically dissimilar decoys.

    Args:
        active_smiles: SMILES string of the active compound.
        n_decoys: Target number of decoys to generate.
        seed: Random seed for reproducibility.
        mw_tolerance: Fractional MW tolerance (0.25 = +/-25%).
        logp_tolerance: Absolute LogP tolerance.
        rotbond_tolerance: Absolute rotatable bond tolerance.
        max_tanimoto: Maximum Tanimoto similarity (lower = more dissimilar).

    Returns:
        List of decoy SMILES strings.
    """
    active_mol = Chem.MolFromSmiles(active_smiles)
    if active_mol is None:
        logger.warning("Invalid active SMILES: %s", active_smiles)
        return []

    active_props = _compute_properties(active_mol)
    active_fp = _fingerprint(active_mol)

    candidates = _enumerate_candidates(seed=seed)
    decoys = []

    for smi in candidates:
        if len(decoys) >= n_decoys:
            break

        mol = Chem.MolFromSmiles(smi)
        if mol is None:
            continue

        props = _compute_properties(mol)

        # Property matching filters
        if active_props["mw"] > 0:
            mw_diff = abs(props["mw"] - active_props["mw"]) / active_props["mw"]
            if mw_diff > mw_tolerance:
                continue

        if abs(props["logp"] - active_props["logp"]) > logp_tolerance:
            continue

        if abs(props["rotatable_bonds"] - active_props["rotatable_bonds"]) > rotbond_tolerance:
            continue

        # Topological dissimilarity filter
        fp = _fingerprint(mol)
        sim = DataStructs.TanimotoSimilarity(active_fp, fp)
        if sim >= max_tanimoto:
            continue

        decoys.append(smi)

    logger.info(
        "Generated %d decoys for active (MW=%.0f, LogP=%.1f)",
        len(decoys),
        active_props["mw"],
        active_props["logp"],
    )
    return decoys


def generate_all_decoys(
    n_per_active: int = 30,
    seed: int = 42,
) -> pd.DataFrame:
    """Generate decoys for all 8 known actives.

    Args:
        n_per_active: Target number of decoys per active.
        seed: Random seed.

    Returns:
        DataFrame with columns: smiles, source_active, is_decoy
    """
    rows = []

    for active in KNOWN_ACTIVES:
        decoy_smiles = generate_decoys_for_active(
            active["smiles"],
            n_decoys=n_per_active,
            seed=seed,
        )
        for smi in decoy_smiles:
            rows.append({
                "smiles": smi,
                "source_active": active["name"],
                "is_decoy": True,
            })

    df = pd.DataFrame(rows)
    logger.info("Generated %d total decoys for %d actives", len(df), len(KNOWN_ACTIVES))
    return df


def save_decoys(
    n_per_active: int = 30,
    seed: int = 42,
    output_dir: Optional[Path] = None,
) -> Path:
    """Generate and save all decoys to CSV.

    Args:
        n_per_active: Target number of decoys per active.
        seed: Random seed.
        output_dir: Directory for output. Defaults to DECOYS_DIR.

    Returns:
        Path to the saved CSV file.
    """
    out = output_dir or DECOYS_DIR
    out.mkdir(parents=True, exist_ok=True)
    path = out / "decoys_manifest.csv"
    df = generate_all_decoys(n_per_active=n_per_active, seed=seed)
    df.to_csv(path, index=False)
    logger.info("Saved decoys to %s", path)
    return path


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    save_decoys()
