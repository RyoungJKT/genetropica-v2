"""ESMFold API wrapper for protein structure prediction.

Predicts 3D protein structures from amino acid sequences using
the ESMFold model via the ESM Metagenomic Atlas API. Suitable
for single-sequence prediction without MSA.
"""

import logging
import time
from pathlib import Path
from typing import Optional

import requests

from src.utils.config import STRUCTURES_DIR

logger = logging.getLogger(__name__)

_ESMFOLD_URL = "https://api.esmatlas.com/foldSequence/v1/pdb/"
_MAX_RETRIES = 3
_RETRY_DELAY = 5  # seconds


def predict_structure(
    sequence: str,
    output_path: Optional[Path] = None,
    name: str = "predicted",
) -> Optional[Path]:
    """Predict protein structure from sequence using ESMFold API.

    Sends a POST request with the amino acid sequence to ESMFold
    and receives a PDB-format structure with pLDDT confidence scores
    stored in the B-factor column.

    Args:
        sequence: Amino acid sequence (single-letter code, e.g. 'MKFLV...').
        output_path: Where to save the PDB file. Defaults to
            STRUCTURES_DIR / ESM-{name}.pdb.
        name: Identifier for the output file.

    Returns:
        Path to the predicted PDB file, or None on failure.
    """
    # Clean the sequence
    seq_clean = sequence.strip().upper().replace(" ", "").replace("\n", "")

    if not seq_clean:
        logger.error("Empty sequence provided")
        return None

    if len(seq_clean) > 400:
        logger.warning(
            "Sequence length %d exceeds recommended ESMFold limit (400 residues). "
            "Consider using ColabFold for longer sequences.",
            len(seq_clean),
        )

    if output_path is None:
        output_path = STRUCTURES_DIR / f"ESM-{name}.pdb"

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Check if already predicted
    if output_path.exists():
        logger.info("ESMFold prediction already exists: %s", output_path)
        return output_path

    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            logger.info(
                "ESMFold prediction attempt %d/%d for %s (%d residues)...",
                attempt, _MAX_RETRIES, name, len(seq_clean),
            )

            resp = requests.post(
                _ESMFOLD_URL,
                data=seq_clean,
                headers={"Content-Type": "text/plain"},
                timeout=120,
            )

            if resp.status_code == 200:
                pdb_text = resp.text
                if pdb_text.startswith(("HEADER", "ATOM", "MODEL", "REMARK")):
                    output_path.write_text(pdb_text)
                    plddt = extract_mean_plddt(output_path)
                    logger.info(
                        "ESMFold prediction saved: %s (mean pLDDT: %.1f)",
                        output_path.name, plddt,
                    )
                    return output_path
                else:
                    logger.warning("Unexpected response format from ESMFold")

            elif resp.status_code == 429:
                logger.warning("ESMFold rate limited, waiting %ds...", _RETRY_DELAY * attempt)
                time.sleep(_RETRY_DELAY * attempt)
                continue

            elif resp.status_code == 422:
                logger.error("Invalid sequence for ESMFold: %s...", seq_clean[:30])
                return None

            else:
                logger.warning(
                    "ESMFold returned status %d: %s",
                    resp.status_code, resp.text[:200],
                )

        except requests.Timeout:
            logger.warning("ESMFold request timed out (attempt %d)", attempt)
        except requests.RequestException as e:
            logger.warning("ESMFold request failed: %s", e)

        if attempt < _MAX_RETRIES:
            time.sleep(_RETRY_DELAY)

    logger.error("ESMFold prediction failed after %d attempts for %s", _MAX_RETRIES, name)
    return None


def extract_mean_plddt(pdb_path: Path) -> float:
    """Extract the mean pLDDT score from an ESMFold PDB file.

    pLDDT (predicted Local Distance Difference Test) is stored
    in the B-factor column of ATOM records. Values range from
    0 to 100, with >70 considered confident and >90 very confident.

    Args:
        pdb_path: Path to ESMFold output PDB.

    Returns:
        Mean pLDDT score across all CA atoms, or 0.0 if parsing fails.
    """
    plddt_values = extract_plddt_per_residue(pdb_path)
    if not plddt_values:
        return 0.0
    return sum(plddt_values) / len(plddt_values)


def extract_plddt_per_residue(pdb_path: Path) -> list[float]:
    """Extract per-residue pLDDT scores from an ESMFold PDB.

    Uses only CA (alpha carbon) atoms to get one score per residue.

    Args:
        pdb_path: Path to ESMFold output PDB.

    Returns:
        List of pLDDT scores, one per residue.
    """
    plddt_values = []

    if not pdb_path.exists():
        return plddt_values

    with open(pdb_path) as f:
        for line in f:
            if line.startswith("ATOM") and line[12:16].strip() == "CA":
                try:
                    bfactor = float(line[60:66].strip())
                    plddt_values.append(bfactor)
                except (ValueError, IndexError):
                    continue

    return plddt_values


def predict_for_target(
    target_id: str, sequence: Optional[str] = None,
) -> Optional[Path]:
    """Predict structure for a GeneTropica target.

    If no sequence is provided, attempts to read the FASTA file
    from the structures directory.

    Args:
        target_id: Target identifier (e.g. 'DENV_NS3').
        sequence: Optional amino acid sequence.

    Returns:
        Path to predicted PDB, or None on failure.
    """
    from src.utils.config import TARGET_PROTEINS

    if target_id not in TARGET_PROTEINS:
        logger.error("Unknown target: %s", target_id)
        return None

    info = TARGET_PROTEINS[target_id]

    # Try to read sequence from FASTA if not provided
    if sequence is None:
        fasta_path = STRUCTURES_DIR / f"{info['uniprot_id']}.fasta"
        if fasta_path.exists():
            sequence = _read_fasta(fasta_path)
        else:
            logger.error("No sequence available for %s", target_id)
            return None

    return predict_structure(
        sequence,
        name=target_id,
    )


def _read_fasta(fasta_path: Path) -> str:
    """Read sequence from a FASTA file, ignoring header lines."""
    lines = []
    with open(fasta_path) as f:
        for line in f:
            if not line.startswith(">"):
                lines.append(line.strip())
    return "".join(lines)
