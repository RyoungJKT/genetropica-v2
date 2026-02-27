"""SDF to PDBQT ligand conversion pipeline.

Generates 3D coordinates from SMILES and converts to PDBQT format
for AutoDock Vina docking.
"""

import logging
import subprocess
from pathlib import Path
from typing import Optional

from src.utils.config import DB_PATH, LIGANDS_DIR
from src.utils.db import get_connection

logger = logging.getLogger(__name__)


def smiles_to_3d(smiles: str, output_path: Path) -> bool:
    """Generate 3D coordinates from a SMILES string using RDKit.

    Writes an SDF file with optimized 3D geometry.

    Args:
        smiles: SMILES string of the molecule.
        output_path: Path for the output SDF file.

    Returns:
        True if successful, False otherwise.
    """
    try:
        from rdkit import Chem
        from rdkit.Chem import AllChem
    except ImportError:
        logger.error("RDKit not installed. Install with: conda install -c conda-forge rdkit")
        return False

    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        logger.warning("Invalid SMILES: %s", smiles)
        return False

    # Add hydrogens for realistic 3D geometry
    mol = Chem.AddHs(mol)

    # Generate 3D coordinates using ETKDG
    result = AllChem.EmbedMolecule(mol, AllChem.ETKDGv3())
    if result != 0:
        # Fallback: try with random coordinates
        result = AllChem.EmbedMolecule(mol, AllChem.ETKDGv3(), randomSeed=42)
        if result != 0:
            logger.warning("Failed to generate 3D coords for SMILES: %s", smiles)
            return False

    # Optimize geometry with MMFF94 force field
    try:
        AllChem.MMFFOptimizeMolecule(mol, maxIters=500)
    except Exception:
        # MMFF may fail for some molecules; UFF is a fallback
        try:
            AllChem.UFFOptimizeMolecule(mol, maxIters=500)
        except Exception:
            logger.warning("Geometry optimization failed for SMILES: %s", smiles)

    # Write to SDF
    output_path.parent.mkdir(parents=True, exist_ok=True)
    writer = Chem.SDWriter(str(output_path))
    writer.write(mol)
    writer.close()

    logger.info("Generated 3D structure: %s", output_path)
    return True


def convert_to_pdbqt(input_path: Path, output_path: Path) -> bool:
    """Convert SDF/MOL2 file to PDBQT format using Open Babel.

    Args:
        input_path: Path to the input SDF or MOL2 file.
        output_path: Path for the output PDBQT file.

    Returns:
        True if conversion succeeded, False otherwise.
    """
    if not input_path.exists():
        logger.warning("Input file not found: %s", input_path)
        return False

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Determine input format from extension
    suffix = input_path.suffix.lower()
    input_format = {".sdf": "sdf", ".mol2": "mol2", ".pdb": "pdb"}.get(suffix, "sdf")

    cmd = [
        "obabel",
        str(input_path),
        "-i", input_format,
        "-o", "pdbqt",
        "-O", str(output_path),
        "--gen3d" if suffix != ".sdf" else "",
        "-h",  # add hydrogens
    ]
    # Remove empty strings from command
    cmd = [c for c in cmd if c]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode == 0 and output_path.exists():
            logger.info("Converted %s -> %s", input_path.name, output_path.name)
            return True
        else:
            logger.warning(
                "Open Babel conversion failed for %s: %s",
                input_path, result.stderr,
            )
            return False
    except FileNotFoundError:
        logger.error(
            "Open Babel (obabel) not found. Install with: "
            "conda install -c conda-forge openbabel"
        )
        return False
    except subprocess.TimeoutExpired:
        logger.warning("Open Babel timed out for %s", input_path)
        return False


def batch_prepare(
    drug_list: list[dict],
    output_dir: Optional[Path] = None,
    db_path: Optional[Path] = None,
) -> dict[str, Path]:
    """Process all drugs: SMILES -> 3D SDF -> PDBQT.

    Args:
        drug_list: List of drug dicts with 'name' and 'smiles' keys.
        output_dir: Directory for output files. Defaults to LIGANDS_DIR.
        db_path: Optional database path override.

    Returns:
        Dict mapping drug_id to PDBQT path for successfully processed drugs.
    """
    dest_dir = output_dir or LIGANDS_DIR
    dest_dir.mkdir(parents=True, exist_ok=True)
    sdf_dir = dest_dir / "sdf"
    pdbqt_dir = dest_dir / "pdbqt"
    sdf_dir.mkdir(exist_ok=True)
    pdbqt_dir.mkdir(exist_ok=True)

    results = {}
    for drug in drug_list:
        name = drug["name"]
        smiles = drug.get("smiles", "")
        drug_id = name.lower().replace(" ", "_")

        if not smiles:
            logger.warning("No SMILES for %s, skipping", name)
            continue

        sdf_path = sdf_dir / f"{drug_id}.sdf"
        pdbqt_path = pdbqt_dir / f"{drug_id}.pdbqt"

        # Skip if PDBQT already exists
        if pdbqt_path.exists():
            results[drug_id] = pdbqt_path
            continue

        # Step 1: SMILES -> 3D SDF
        if not sdf_path.exists():
            if not smiles_to_3d(smiles, sdf_path):
                continue

        # Step 2: SDF -> PDBQT
        if convert_to_pdbqt(sdf_path, pdbqt_path):
            results[drug_id] = pdbqt_path
            # Update database with file path
            _update_drug_path(drug_id, pdbqt_path, db_path)

    logger.info(
        "Prepared %d/%d ligands successfully",
        len(results), len(drug_list),
    )
    return results


def _update_drug_path(
    drug_id: str, pdbqt_path: Path, db_path: Optional[Path] = None
) -> None:
    """Update a drug's PDBQT path in the database."""
    conn = get_connection(db_path)
    try:
        conn.execute(
            "UPDATE drugs SET pdbqt_path = ? WHERE drug_id = ?",
            (str(pdbqt_path), drug_id),
        )
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    from src.data_acquisition.fetch_drugs import load_curated_drugs

    drugs = load_curated_drugs()
    results = batch_prepare(drugs)
    print(f"Prepared {len(results)} ligands:")
    for drug_id, path in list(results.items())[:5]:
        print(f"  {drug_id}: {path}")
    if len(results) > 5:
        print(f"  ... and {len(results) - 5} more")
