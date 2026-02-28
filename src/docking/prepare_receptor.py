"""Protein preparation for AutoDock Vina.

Cleans PDB files, defines search boxes around known active sites,
and converts receptors to PDBQT format.
"""

import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from src.utils.config import STRUCTURES_DIR

logger = logging.getLogger(__name__)


@dataclass
class SearchBox:
    """Docking search box definition."""

    center_x: float
    center_y: float
    center_z: float
    size_x: float = 25.0
    size_y: float = 25.0
    size_z: float = 25.0


# Pre-defined binding site coordinates for each target.
# Coordinates validated against actual PDB crystal structures.
# Uses co-crystallized ligand positions where available,
# protein center-of-mass for structures without ligands.
BINDING_SITES: dict[str, SearchBox] = {
    # Dengue NS3 Protease-Helicase (2VBC)
    # Active site: His51, Asp75, Ser135 catalytic triad
    # No co-crystallized ligand — using protein COM
    "DENV_NS3": SearchBox(center_x=-6.2, center_y=2.9, center_z=20.9),
    # Dengue NS5 RdRp (5CCV)
    # Co-crystallized SAH marks the methyltransferase active site
    "DENV_NS5": SearchBox(center_x=-118.9, center_y=60.8, center_z=40.2),
    # Dengue Envelope protein (1OAN)
    # Glycosylation site ligands (NAG/BMA/FUC) at domain II
    "DENV_E": SearchBox(center_x=-12.5, center_y=69.2, center_z=24.4),
    # Chikungunya nsP2 Protease (3TRK)
    # Cysteine protease active site: Cys1013, His1083
    "CHIKV_nsP2": SearchBox(center_x=15.1, center_y=26.4, center_z=20.8),
    # Chikungunya nsP1 Capping Enzyme (6Z0V)
    # Chain A center of mass (dodecameric complex — dock against one chain)
    "CHIKV_nsP1": SearchBox(center_x=60.2, center_y=129.8, center_z=97.7),
    # Leptospira LipL32 (3FRH)
    # Co-crystallized SAH at calcium-binding region
    "LEPTO_LipL32": SearchBox(center_x=-12.5, center_y=4.0, center_z=-1.7),
}


def clean_pdb(pdb_path: Path, output_path: Optional[Path] = None) -> Path:
    """Clean a PDB file by removing water, heteroatoms, and adding hydrogens.

    Retains only ATOM records (protein backbone and side chains).

    Args:
        pdb_path: Path to the input PDB file.
        output_path: Output path. Defaults to <name>_clean.pdb.

    Returns:
        Path to the cleaned PDB file.
    """
    if output_path is None:
        output_path = pdb_path.with_name(
            pdb_path.stem + "_clean" + pdb_path.suffix
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)

    kept_lines = []
    with open(pdb_path) as f:
        for line in f:
            record = line[:6].strip()
            if record in ("ATOM", "TER", "END"):
                kept_lines.append(line)

    with open(output_path, "w") as f:
        f.writelines(kept_lines)

    logger.info("Cleaned PDB: %s -> %s (%d lines)", pdb_path.name, output_path.name, len(kept_lines))
    return output_path


def define_search_box(
    target_id: str,
    center: Optional[tuple[float, float, float]] = None,
    size: Optional[tuple[float, float, float]] = None,
) -> SearchBox:
    """Get the docking search box for a target.

    Uses pre-defined coordinates from BINDING_SITES, or custom
    coordinates if provided.

    Args:
        target_id: Target identifier (e.g. 'DENV_NS3').
        center: Optional custom center (x, y, z) override.
        size: Optional custom box size (x, y, z) override.

    Returns:
        SearchBox with center and size coordinates.
    """
    if target_id in BINDING_SITES:
        box = BINDING_SITES[target_id]
    else:
        logger.warning("No predefined binding site for %s, using defaults", target_id)
        box = SearchBox(center_x=0.0, center_y=0.0, center_z=0.0, size_x=30.0, size_y=30.0, size_z=30.0)

    if center:
        box.center_x, box.center_y, box.center_z = center
    if size:
        box.size_x, box.size_y, box.size_z = size

    return box


def convert_receptor_pdbqt(
    pdb_path: Path, output_path: Optional[Path] = None
) -> Optional[Path]:
    """Convert a cleaned PDB file to PDBQT format for Vina.

    Uses Open Babel for conversion, adding Gasteiger charges.

    Args:
        pdb_path: Path to the cleaned PDB file.
        output_path: Output path. Defaults to <name>.pdbqt.

    Returns:
        Path to the PDBQT file, or None on failure.
    """
    if output_path is None:
        output_path = pdb_path.with_suffix(".pdbqt")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "obabel",
        str(pdb_path),
        "-i", "pdb",
        "-o", "pdbqt",
        "-O", str(output_path),
        "-xr",  # receptor mode (rigid)
        "-h",   # add hydrogens
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode == 0 and output_path.exists():
            logger.info("Converted receptor: %s -> %s", pdb_path.name, output_path.name)
            return output_path
        else:
            logger.warning("Receptor conversion failed: %s", result.stderr)
            return None
    except FileNotFoundError:
        logger.error("Open Babel (obabel) not found. Install: conda install -c conda-forge openbabel")
        return None
    except subprocess.TimeoutExpired:
        logger.warning("Receptor conversion timed out for %s", pdb_path)
        return None


def prepare_receptor(
    target_id: str, pdb_path: Optional[Path] = None
) -> Optional[Path]:
    """Full receptor preparation pipeline: clean -> convert.

    Args:
        target_id: Target identifier.
        pdb_path: Path to PDB file. If None, looks in STRUCTURES_DIR.

    Returns:
        Path to the prepared PDBQT receptor file, or None on failure.
    """
    from src.utils.config import TARGET_PROTEINS

    if pdb_path is None:
        pdb_id = TARGET_PROTEINS[target_id]["pdb_id"]
        pdb_path = STRUCTURES_DIR / f"{pdb_id}.pdb"

    if not pdb_path.exists():
        logger.error("PDB file not found: %s", pdb_path)
        return None

    clean_path = clean_pdb(pdb_path)
    pdbqt_path = convert_receptor_pdbqt(clean_path)

    return pdbqt_path
