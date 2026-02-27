"""PLIP interaction profiling for docked poses.

Uses distance-based heuristics to identify protein-ligand interactions
from docked pose coordinates. This is a simplified approach that does
not require PLIP installation — it classifies contacts by distance and
atom type.
"""

import logging
import math
from pathlib import Path
from typing import Optional

from src.utils.db import get_connection

logger = logging.getLogger(__name__)

# Distance thresholds (angstroms) for interaction classification
_HBOND_MAX = 3.5
_HYDROPHOBIC_MAX = 4.5
_IONIC_MAX = 4.0
_PISTACK_MAX = 5.5

# Standard amino acid 3-letter codes
_AMINO_ACIDS = {
    "ALA", "ARG", "ASN", "ASP", "CYS", "GLN", "GLU", "GLY", "HIS", "ILE",
    "LEU", "LYS", "MET", "PHE", "PRO", "SER", "THR", "TRP", "TYR", "VAL",
}

# Residues that form hydrogen bonds
_HBOND_DONORS = {"ARG", "ASN", "GLN", "HIS", "LYS", "SER", "THR", "TRP", "TYR", "CYS"}
_HBOND_ACCEPTORS = {"ASN", "ASP", "GLN", "GLU", "HIS", "SER", "THR", "TYR", "CYS"}

# Hydrophobic residues
_HYDROPHOBIC = {"ALA", "ILE", "LEU", "MET", "PHE", "PRO", "TRP", "TYR", "VAL"}

# Charged residues for ionic/salt-bridge interactions
_POSITIVE = {"ARG", "HIS", "LYS"}
_NEGATIVE = {"ASP", "GLU"}

# Aromatic residues for pi-stacking
_AROMATIC = {"PHE", "TRP", "TYR", "HIS"}


def _parse_coordinates(line: str) -> Optional[tuple[float, float, float]]:
    """Extract x, y, z coordinates from a PDB/PDBQT ATOM line."""
    if len(line) < 54:
        return None
    try:
        x = float(line[30:38])
        y = float(line[38:46])
        z = float(line[46:54])
        return (x, y, z)
    except ValueError:
        return None


def _parse_residue_info(line: str) -> Optional[dict]:
    """Extract residue name, number, and chain from a PDB/PDBQT ATOM line."""
    if len(line) < 27:
        return None
    try:
        return {
            "residue_name": line[17:20].strip(),
            "residue_number": int(line[22:26].strip()),
            "chain": line[21].strip() or "A",
            "atom_name": line[12:16].strip(),
        }
    except (ValueError, IndexError):
        return None


def _distance(coord1: tuple, coord2: tuple) -> float:
    """Euclidean distance between two 3D points."""
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(coord1, coord2)))


def _classify_interaction(
    res_name: str, dist: float, atom_name: str
) -> Optional[str]:
    """Classify an interaction based on residue type and distance.

    Args:
        res_name: 3-letter residue name.
        dist: Distance in angstroms.
        atom_name: Atom name from the residue.

    Returns:
        Interaction type string, or None if no significant interaction.
    """
    if dist <= _HBOND_MAX:
        if res_name in _HBOND_DONORS or res_name in _HBOND_ACCEPTORS:
            if atom_name.startswith(("N", "O", "S")):
                return "Hydrogen Bond"
        if res_name in _POSITIVE or res_name in _NEGATIVE:
            return "Salt Bridge"

    if dist <= _IONIC_MAX and (res_name in _POSITIVE or res_name in _NEGATIVE):
        return "Ionic"

    if dist <= _HYDROPHOBIC_MAX and res_name in _HYDROPHOBIC:
        if atom_name.startswith("C"):
            return "Hydrophobic"

    if dist <= _PISTACK_MAX and res_name in _AROMATIC:
        return "Pi-Stacking"

    return None


def analyze_interactions(
    receptor_path: Path,
    ligand_path: Path,
    contact_cutoff: float = 5.5,
) -> list[dict]:
    """Identify protein-ligand interactions from docked pose files.

    Uses distance-based heuristics to classify contacts between
    receptor residues and ligand atoms.

    Args:
        receptor_path: Path to receptor PDB/PDBQT file.
        ligand_path: Path to ligand pose PDB/PDBQT file.
        contact_cutoff: Maximum distance to consider (angstroms).

    Returns:
        List of interaction dicts with keys: residue_name, residue_number,
        chain, interaction_type, distance.
    """
    # Parse receptor atoms
    receptor_atoms = []
    if receptor_path.exists():
        with open(receptor_path) as f:
            for line in f:
                if line.startswith(("ATOM", "HETATM")):
                    coords = _parse_coordinates(line)
                    res_info = _parse_residue_info(line)
                    if coords and res_info and res_info["residue_name"] in _AMINO_ACIDS:
                        receptor_atoms.append({"coords": coords, **res_info})

    # Parse ligand atoms
    ligand_coords = []
    if ligand_path.exists():
        with open(ligand_path) as f:
            for line in f:
                if line.startswith(("ATOM", "HETATM")):
                    coords = _parse_coordinates(line)
                    if coords:
                        ligand_coords.append(coords)

    if not receptor_atoms or not ligand_coords:
        logger.warning("No atoms parsed — check file formats")
        return []

    # Find contacts within cutoff
    seen = set()
    interactions = []

    for rec_atom in receptor_atoms:
        for lig_coord in ligand_coords:
            dist = _distance(rec_atom["coords"], lig_coord)

            if dist > contact_cutoff:
                continue

            res_key = (rec_atom["residue_name"], rec_atom["residue_number"], rec_atom["chain"])
            if res_key in seen:
                continue

            interaction_type = _classify_interaction(
                rec_atom["residue_name"], dist, rec_atom["atom_name"]
            )

            if interaction_type:
                seen.add(res_key)
                interactions.append({
                    "residue_name": rec_atom["residue_name"],
                    "residue_number": rec_atom["residue_number"],
                    "chain": rec_atom["chain"],
                    "interaction_type": interaction_type,
                    "distance": round(dist, 2),
                })

    interactions.sort(key=lambda x: (x["interaction_type"], x["residue_number"]))
    logger.info("Found %d interactions between %s and %s",
                len(interactions), receptor_path.name, ligand_path.name)
    return interactions


def store_interactions(
    drug_id: str,
    target_id: str,
    interactions: list[dict],
    pose_rank: int = 1,
    db_path: Optional[Path] = None,
) -> None:
    """Store interaction data in the database.

    Args:
        drug_id: Drug identifier.
        target_id: Target identifier.
        interactions: List of interaction dicts from analyze_interactions.
        pose_rank: Pose rank (default 1 for best pose).
        db_path: Optional database path override.
    """
    conn = get_connection(db_path)
    try:
        # Clear existing interactions for this drug-target-pose
        conn.execute(
            "DELETE FROM interactions WHERE drug_id = ? AND target_id = ? AND pose_rank = ?",
            (drug_id, target_id, pose_rank),
        )

        for inter in interactions:
            conn.execute(
                """INSERT INTO interactions
                   (drug_id, target_id, pose_rank, residue_name,
                    residue_number, chain, interaction_type, distance)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    drug_id, target_id, pose_rank,
                    inter["residue_name"], inter["residue_number"],
                    inter["chain"], inter["interaction_type"],
                    inter["distance"],
                ),
            )
        conn.commit()
        logger.info("Stored %d interactions for %s/%s", len(interactions), drug_id, target_id)
    finally:
        conn.close()
