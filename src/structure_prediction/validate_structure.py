"""Structure quality validation checks.

Assesses predicted protein structures for suitability in molecular
docking: pLDDT confidence, steric clashes, and comparison with
experimental structures when available.
"""

import logging
import math
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Quality thresholds
_PLDDT_CONFIDENT = 70.0    # Minimum pLDDT for confident regions
_PLDDT_VERY_CONFIDENT = 90.0
_CLASH_DISTANCE = 1.5      # Angstroms — atoms closer than this are clashing
_DOCKING_PLDDT_MIN = 70.0  # Minimum mean pLDDT for docking suitability


def check_plddt(pdb_path: Path) -> dict:
    """Extract and assess per-residue pLDDT confidence scores.

    pLDDT is stored in the B-factor column for ESMFold/AlphaFold
    predicted structures. Scores range from 0-100.

    Args:
        pdb_path: Path to predicted PDB file.

    Returns:
        Dict with 'mean_plddt', 'median_plddt', 'min_plddt',
        'n_residues', 'pct_confident' (>70), 'pct_very_confident' (>90),
        and 'per_residue' list.
    """
    plddt_values = []

    if not pdb_path.exists():
        logger.warning("PDB file not found: %s", pdb_path)
        return _empty_plddt_result()

    with open(pdb_path) as f:
        for line in f:
            if line.startswith("ATOM") and line[12:16].strip() == "CA":
                try:
                    bfactor = float(line[60:66].strip())
                    plddt_values.append(bfactor)
                except (ValueError, IndexError):
                    continue

    if not plddt_values:
        logger.warning("No CA atoms found in %s", pdb_path.name)
        return _empty_plddt_result()

    sorted_vals = sorted(plddt_values)
    n = len(sorted_vals)
    median = sorted_vals[n // 2] if n % 2 else (sorted_vals[n // 2 - 1] + sorted_vals[n // 2]) / 2

    n_confident = sum(1 for v in plddt_values if v >= _PLDDT_CONFIDENT)
    n_very = sum(1 for v in plddt_values if v >= _PLDDT_VERY_CONFIDENT)

    return {
        "mean_plddt": round(sum(plddt_values) / n, 2),
        "median_plddt": round(median, 2),
        "min_plddt": round(min(plddt_values), 2),
        "n_residues": n,
        "pct_confident": round(100.0 * n_confident / n, 1),
        "pct_very_confident": round(100.0 * n_very / n, 1),
        "per_residue": plddt_values,
    }


def _empty_plddt_result() -> dict:
    """Return an empty pLDDT result dict."""
    return {
        "mean_plddt": 0.0,
        "median_plddt": 0.0,
        "min_plddt": 0.0,
        "n_residues": 0,
        "pct_confident": 0.0,
        "pct_very_confident": 0.0,
        "per_residue": [],
    }


def check_clashes(pdb_path: Path, threshold: float = _CLASH_DISTANCE) -> dict:
    """Detect steric clashes in a protein structure.

    Finds pairs of non-bonded atoms closer than the clash threshold.

    Args:
        pdb_path: Path to PDB file.
        threshold: Distance threshold in angstroms (default 1.5).

    Returns:
        Dict with 'n_clashes', 'n_atoms', 'clash_ratio',
        and 'clashes' list of (atom1, atom2, distance) tuples.
    """
    atoms = []

    if not pdb_path.exists():
        return {"n_clashes": 0, "n_atoms": 0, "clash_ratio": 0.0, "clashes": []}

    with open(pdb_path) as f:
        for line in f:
            if line.startswith("ATOM"):
                try:
                    x = float(line[30:38])
                    y = float(line[38:46])
                    z = float(line[46:54])
                    atom_name = line[12:16].strip()
                    res_num = int(line[22:26].strip())
                    atoms.append({
                        "name": atom_name,
                        "res_num": res_num,
                        "coords": (x, y, z),
                    })
                except (ValueError, IndexError):
                    continue

    clashes = []
    n_atoms = len(atoms)

    # Only check non-bonded atoms (residues > 1 apart)
    for i in range(n_atoms):
        for j in range(i + 1, min(i + 50, n_atoms)):  # Limit search radius
            if abs(atoms[i]["res_num"] - atoms[j]["res_num"]) <= 1:
                continue  # Skip bonded/adjacent residues

            dist = _distance(atoms[i]["coords"], atoms[j]["coords"])
            if dist < threshold:
                clashes.append((
                    f"{atoms[i]['name']}:{atoms[i]['res_num']}",
                    f"{atoms[j]['name']}:{atoms[j]['res_num']}",
                    round(dist, 3),
                ))

    n_possible = max(n_atoms * (n_atoms - 1) // 2, 1)
    clash_ratio = len(clashes) / n_possible

    logger.info(
        "Clash check: %d clashes among %d atoms (ratio: %.6f)",
        len(clashes), n_atoms, clash_ratio,
    )

    return {
        "n_clashes": len(clashes),
        "n_atoms": n_atoms,
        "clash_ratio": round(clash_ratio, 6),
        "clashes": clashes[:20],  # Return top 20 clashes only
    }


def compare_to_experimental(
    predicted_path: Path,
    experimental_path: Path,
) -> dict:
    """Calculate RMSD between predicted and experimental structures.

    Compares CA atom positions between two PDB files. Assumes
    both structures have the same sequence and residue numbering.

    Args:
        predicted_path: Path to predicted PDB file.
        experimental_path: Path to experimental PDB file.

    Returns:
        Dict with 'rmsd', 'n_aligned', and 'quality' assessment.
    """
    pred_cas = _extract_ca_coords(predicted_path)
    exp_cas = _extract_ca_coords(experimental_path)

    if not pred_cas or not exp_cas:
        return {"rmsd": float("inf"), "n_aligned": 0, "quality": "unknown"}

    # Align by residue number
    common_residues = set(pred_cas.keys()) & set(exp_cas.keys())
    if not common_residues:
        return {"rmsd": float("inf"), "n_aligned": 0, "quality": "no_overlap"}

    sq_diffs = []
    for res_num in sorted(common_residues):
        d = _distance(pred_cas[res_num], exp_cas[res_num])
        sq_diffs.append(d ** 2)

    rmsd = math.sqrt(sum(sq_diffs) / len(sq_diffs))

    if rmsd < 2.0:
        quality = "excellent"
    elif rmsd < 4.0:
        quality = "good"
    elif rmsd < 6.0:
        quality = "moderate"
    else:
        quality = "poor"

    logger.info(
        "RMSD comparison: %.2f A over %d residues (%s)",
        rmsd, len(common_residues), quality,
    )

    return {
        "rmsd": round(rmsd, 3),
        "n_aligned": len(common_residues),
        "quality": quality,
    }


def _extract_ca_coords(pdb_path: Path) -> dict[int, tuple[float, float, float]]:
    """Extract CA atom coordinates indexed by residue number."""
    coords = {}
    if not pdb_path.exists():
        return coords

    with open(pdb_path) as f:
        for line in f:
            if line.startswith("ATOM") and line[12:16].strip() == "CA":
                try:
                    res_num = int(line[22:26].strip())
                    x = float(line[30:38])
                    y = float(line[38:46])
                    z = float(line[46:54])
                    coords[res_num] = (x, y, z)
                except (ValueError, IndexError):
                    continue
    return coords


def _distance(c1: tuple, c2: tuple) -> float:
    """Euclidean distance between two 3D points."""
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(c1, c2)))


def generate_quality_report(pdb_path: Path) -> dict:
    """Generate a comprehensive quality report for a structure.

    Args:
        pdb_path: Path to PDB file (predicted or experimental).

    Returns:
        Dict with 'plddt' (pLDDT assessment), 'clashes' (clash report),
        'suitable_for_docking' (bool), and 'recommendation'.
    """
    plddt = check_plddt(pdb_path)
    clashes = check_clashes(pdb_path)

    # Docking suitability check
    suitable = (
        plddt["mean_plddt"] >= _DOCKING_PLDDT_MIN
        and plddt["pct_confident"] >= 50.0
        and clashes["n_clashes"] < 10
    )

    # Generate recommendation
    if plddt["n_residues"] == 0:
        recommendation = "No structure data found — cannot assess quality."
    elif suitable:
        recommendation = (
            f"Structure is suitable for docking. "
            f"Mean pLDDT {plddt['mean_plddt']:.1f}, "
            f"{plddt['pct_confident']:.0f}% confident residues."
        )
    elif plddt["mean_plddt"] < _DOCKING_PLDDT_MIN:
        recommendation = (
            f"Low confidence (pLDDT {plddt['mean_plddt']:.1f}). "
            "Consider using ColabFold or obtaining experimental structure."
        )
    else:
        recommendation = (
            f"Structure has quality issues ({clashes['n_clashes']} clashes). "
            "Review manually before docking."
        )

    report = {
        "plddt": plddt,
        "clashes": clashes,
        "suitable_for_docking": suitable,
        "recommendation": recommendation,
    }

    logger.info("Quality report for %s: %s", pdb_path.name, recommendation)
    return report


def is_suitable_for_docking(
    pdb_path: Path,
    binding_site_residues: Optional[list[int]] = None,
) -> bool:
    """Quick check if a structure is suitable for docking.

    Optionally checks pLDDT specifically in the binding site region.

    Args:
        pdb_path: Path to PDB file.
        binding_site_residues: Optional list of residue numbers
            comprising the binding site.

    Returns:
        True if the structure passes quality checks for docking.
    """
    plddt = check_plddt(pdb_path)

    if plddt["n_residues"] == 0:
        return False

    # Check binding site specifically if provided
    if binding_site_residues and plddt["per_residue"]:
        site_scores = []
        for i, score in enumerate(plddt["per_residue"]):
            res_num = i + 1  # Assuming sequential numbering
            if res_num in binding_site_residues:
                site_scores.append(score)

        if site_scores:
            site_mean = sum(site_scores) / len(site_scores)
            if site_mean < _DOCKING_PLDDT_MIN:
                logger.warning(
                    "Binding site pLDDT %.1f is below threshold %.1f",
                    site_mean, _DOCKING_PLDDT_MIN,
                )
                return False

    return plddt["mean_plddt"] >= _DOCKING_PLDDT_MIN
