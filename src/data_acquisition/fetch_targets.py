"""PDB/UniProt protein target retriever.

Downloads protein structures from RCSB PDB, sequences from UniProt,
and predicted structures from the AlphaFold database.
"""

import logging
from pathlib import Path
from typing import Optional

import requests

from src.utils.config import DB_PATH, STRUCTURES_DIR, TARGET_PROTEINS
from src.utils.db import get_connection, init_db

logger = logging.getLogger(__name__)

_RCSB_URL = "https://files.rcsb.org/download/{pdb_id}.pdb"
_UNIPROT_URL = "https://rest.uniprot.org/uniprotkb/{uniprot_id}.fasta"
_ALPHAFOLD_URL = (
    "https://alphafold.ebi.ac.uk/files/AF-{uniprot_id}-F1-model_v4.pdb"
)


def fetch_pdb_structure(
    pdb_id: str, output_dir: Optional[Path] = None
) -> Optional[Path]:
    """Download a PDB file from RCSB.

    Args:
        pdb_id: 4-character PDB identifier (e.g. '2VBC').
        output_dir: Directory to save. Defaults to STRUCTURES_DIR.

    Returns:
        Path to the downloaded PDB file, or None on failure.
    """
    dest_dir = output_dir or STRUCTURES_DIR
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{pdb_id.upper()}.pdb"

    if dest.exists():
        logger.info("PDB %s already exists at %s", pdb_id, dest)
        return dest

    url = _RCSB_URL.format(pdb_id=pdb_id.upper())
    logger.info("Fetching PDB %s from RCSB...", pdb_id)

    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        dest.write_text(resp.text)
        logger.info("Saved PDB %s to %s (%d bytes)", pdb_id, dest, len(resp.text))
        return dest
    except requests.RequestException as e:
        logger.warning("Failed to fetch PDB %s: %s", pdb_id, e)
        return None


def fetch_uniprot_sequence(
    uniprot_id: str, output_dir: Optional[Path] = None
) -> Optional[Path]:
    """Download a protein sequence in FASTA format from UniProt.

    Args:
        uniprot_id: UniProt accession (e.g. 'P27909').
        output_dir: Directory to save. Defaults to STRUCTURES_DIR.

    Returns:
        Path to the saved FASTA file, or None on failure.
    """
    dest_dir = output_dir or STRUCTURES_DIR
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{uniprot_id}.fasta"

    if dest.exists():
        logger.info("UniProt %s already exists at %s", uniprot_id, dest)
        return dest

    url = _UNIPROT_URL.format(uniprot_id=uniprot_id)
    logger.info("Fetching UniProt %s...", uniprot_id)

    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        dest.write_text(resp.text)
        logger.info("Saved UniProt %s to %s", uniprot_id, dest)
        return dest
    except requests.RequestException as e:
        logger.warning("Failed to fetch UniProt %s: %s", uniprot_id, e)
        return None


def fetch_alphafold_structure(
    uniprot_id: str, output_dir: Optional[Path] = None
) -> Optional[Path]:
    """Download a predicted structure from AlphaFold DB.

    Args:
        uniprot_id: UniProt accession.
        output_dir: Directory to save. Defaults to STRUCTURES_DIR.

    Returns:
        Path to the downloaded PDB file, or None if not available.
    """
    dest_dir = output_dir or STRUCTURES_DIR
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"AF-{uniprot_id}.pdb"

    if dest.exists():
        logger.info("AlphaFold %s already exists at %s", uniprot_id, dest)
        return dest

    url = _ALPHAFOLD_URL.format(uniprot_id=uniprot_id)
    logger.info("Checking AlphaFold DB for %s...", uniprot_id)

    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        dest.write_text(resp.text)
        logger.info("Saved AlphaFold structure for %s to %s", uniprot_id, dest)
        return dest
    except requests.RequestException as e:
        logger.info("AlphaFold structure not available for %s: %s", uniprot_id, e)
        return None


def update_target_in_db(
    target_id: str, pdb_path: Optional[Path] = None, db_path: Optional[Path] = None
) -> None:
    """Update a target's file path in the database.

    Args:
        target_id: Target identifier (e.g. 'DENV_NS3').
        pdb_path: Path to the downloaded PDB file.
        db_path: Optional database path override.
    """
    conn = get_connection(db_path)
    try:
        conn.execute(
            "UPDATE targets SET pdbqt_path = ? WHERE target_id = ?",
            (str(pdb_path) if pdb_path else None, target_id),
        )
        conn.commit()
    finally:
        conn.close()


def fetch_all_targets(output_dir: Optional[Path] = None) -> dict[str, Path]:
    """Download PDB structures for all configured targets.

    Args:
        output_dir: Directory to save structures.

    Returns:
        Dict mapping target_id to the path of the downloaded PDB file.
    """
    results = {}
    for target_id, info in TARGET_PROTEINS.items():
        pdb_id = info["pdb_id"]
        path = fetch_pdb_structure(pdb_id, output_dir)
        if path:
            results[target_id] = path
            update_target_in_db(target_id, path)
        else:
            logger.warning("Could not fetch structure for %s (PDB: %s)", target_id, pdb_id)

        # Also fetch UniProt sequence
        uniprot_id = info.get("uniprot_id")
        if uniprot_id:
            fetch_uniprot_sequence(uniprot_id, output_dir)

    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    init_db()
    results = fetch_all_targets()
    print(f"Fetched {len(results)} protein structures:")
    for tid, path in results.items():
        print(f"  {tid}: {path}")
