"""Multiple sequence alignment via EBI Clustal Omega REST API.

Submits multi-FASTA sequences to the EBI Clustal Omega web service,
polls for completion, downloads results, and computes pairwise identity
matrices and per-position conservation scores.
"""

import json
import logging
import time
from collections import Counter
from pathlib import Path
from typing import Optional

import requests as http_requests

from src.utils.config import BASE_DIR

logger = logging.getLogger(__name__)

ALIGNMENT_DIR: Path = BASE_DIR / "data" / "conservation" / "alignment"

EBI_RUN_URL = "https://www.ebi.ac.uk/Tools/services/rest/clustalo/run"
EBI_STATUS_URL = "https://www.ebi.ac.uk/Tools/services/rest/clustalo/status/{job_id}"
EBI_RESULT_URL = (
    "https://www.ebi.ac.uk/Tools/services/rest/clustalo/result/{job_id}/{result_type}"
)


def parse_clustal_alignment(fasta_aln_text: str) -> dict[str, str]:
    """Parse a FASTA-format alignment into {name: aligned_sequence}.

    Handles multi-line sequences and extracts the first token of
    the header as the sequence name.

    Args:
        fasta_aln_text: FASTA alignment text (with gaps as '-').

    Returns:
        Dict mapping sequence name to aligned sequence (with gaps).
    """
    result: dict[str, str] = {}
    current_name: Optional[str] = None
    current_parts: list[str] = []

    for line in fasta_aln_text.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith(">"):
            if current_name is not None:
                result[current_name] = "".join(current_parts)
            # Use the first word/token as name
            current_name = line[1:].split()[0].split("|")[0]
            current_parts = []
        else:
            current_parts.append(line.upper())

    if current_name is not None:
        result[current_name] = "".join(current_parts)

    return result


def compute_pairwise_identity(aligned_seqs: dict[str, str]) -> dict[str, dict[str, float]]:
    """Compute pairwise sequence identity matrix from aligned sequences.

    Identity is calculated as the fraction of non-gap positions where
    both sequences share the same amino acid.

    Args:
        aligned_seqs: Dict mapping name to aligned sequence (with gaps).

    Returns:
        Nested dict: matrix[seq_a][seq_b] = percent identity.
    """
    names = list(aligned_seqs.keys())
    matrix: dict[str, dict[str, float]] = {n: {} for n in names}

    for i, name_a in enumerate(names):
        seq_a = aligned_seqs[name_a]
        for j, name_b in enumerate(names):
            seq_b = aligned_seqs[name_b]
            if i == j:
                matrix[name_a][name_b] = 100.0
                continue

            matches = 0
            total = 0
            for aa_a, aa_b in zip(seq_a, seq_b):
                total += 1
                if aa_a == aa_b and aa_a != "-":
                    matches += 1
            identity = (matches / total * 100) if total > 0 else 0.0
            matrix[name_a][name_b] = round(identity, 1)

    return matrix


def compute_per_position_identity(aligned_seqs: dict[str, str]) -> list[float]:
    """Compute per-position percent identity across all sequences.

    At each alignment column, calculates the fraction of sequences
    sharing the most common non-gap residue.

    Args:
        aligned_seqs: Dict mapping name to aligned sequence.

    Returns:
        List of percent identity values, one per alignment column.
    """
    seqs = list(aligned_seqs.values())
    if not seqs:
        return []

    aln_len = len(seqs[0])
    scores: list[float] = []

    for pos in range(aln_len):
        residues = [s[pos] for s in seqs if pos < len(s)]
        non_gap = [r for r in residues if r != "-"]
        if not non_gap:
            scores.append(0.0)
            continue
        counts = Counter(non_gap)
        most_common_count = counts.most_common(1)[0][1]
        scores.append(round(most_common_count / len(residues) * 100, 1))

    return scores


def submit_alignment(
    fasta_text: str,
    email: str = "genetropica@example.com",
    timeout: int = 30,
) -> Optional[str]:
    """Submit sequences to EBI Clustal Omega REST API.

    Args:
        fasta_text: Multi-FASTA sequences to align.
        email: Required email for EBI job submission.
        timeout: HTTP request timeout.

    Returns:
        Job ID string, or None on failure.
    """
    try:
        resp = http_requests.post(
            EBI_RUN_URL,
            data={
                "email": email,
                "sequence": fasta_text,
                "outfmt": "fa",
            },
            timeout=timeout,
        )
        resp.raise_for_status()
        job_id = resp.text.strip()
        logger.info("Clustal Omega job submitted: %s", job_id)
        return job_id
    except Exception as e:
        logger.error("Failed to submit alignment job: %s", e)
        return None


def poll_job(
    job_id: str,
    max_wait: int = 300,
    poll_interval: int = 5,
) -> bool:
    """Poll EBI job until completion.

    Args:
        job_id: EBI job identifier.
        max_wait: Maximum wait time in seconds.
        poll_interval: Seconds between status checks.

    Returns:
        True if job finished successfully, False otherwise.
    """
    elapsed = 0
    while elapsed < max_wait:
        try:
            resp = http_requests.get(
                EBI_STATUS_URL.format(job_id=job_id),
                timeout=10,
            )
            status = resp.text.strip()
            logger.info("Job %s status: %s", job_id, status)

            if status == "FINISHED":
                return True
            elif status in ("FAILURE", "ERROR", "NOT_FOUND"):
                logger.error("Job %s failed: %s", job_id, status)
                return False
        except Exception as e:
            logger.warning("Poll error: %s", e)

        time.sleep(poll_interval)
        elapsed += poll_interval

    logger.error("Job %s timed out after %ds", job_id, max_wait)
    return False


def download_result(
    job_id: str,
    result_type: str = "aln-fasta",
) -> Optional[str]:
    """Download alignment result from EBI.

    Args:
        job_id: EBI job identifier.
        result_type: Result format ('aln-fasta', 'aln-clustal_num', 'pim').

    Returns:
        Result text, or None on failure.
    """
    try:
        resp = http_requests.get(
            EBI_RESULT_URL.format(job_id=job_id, result_type=result_type),
            timeout=30,
        )
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        logger.error("Failed to download result: %s", e)
        return None


def run_alignment(
    fasta_text: str,
    output_dir: Optional[Path] = None,
) -> Optional[dict[str, str]]:
    """Run full Clustal Omega alignment pipeline.

    Submits sequences, polls for completion, downloads and parses results.

    Args:
        fasta_text: Multi-FASTA sequences to align.
        output_dir: Directory for output files. Defaults to ALIGNMENT_DIR.

    Returns:
        Dict mapping sequence name to aligned sequence, or None on failure.
    """
    out = output_dir or ALIGNMENT_DIR
    out.mkdir(parents=True, exist_ok=True)

    # Submit
    job_id = submit_alignment(fasta_text)
    if job_id is None:
        return None

    # Poll
    if not poll_job(job_id):
        return None

    # Download FASTA alignment
    aln_fasta = download_result(job_id, "aln-fasta")
    if aln_fasta is None:
        return None

    # Save alignment files
    (out / "alignment.fasta").write_text(aln_fasta)
    logger.info("Alignment saved to %s", out / "alignment.fasta")

    # Also try to download clustal format
    aln_clustal = download_result(job_id, "aln-clustal_num")
    if aln_clustal:
        (out / "alignment.aln").write_text(aln_clustal)

    # Parse and return
    aligned = parse_clustal_alignment(aln_fasta)
    logger.info("Alignment parsed: %d sequences", len(aligned))

    # Save pairwise identity matrix
    identity_matrix = compute_pairwise_identity(aligned)
    (out / "pairwise_identity.json").write_text(
        json.dumps(identity_matrix, indent=2)
    )

    return aligned
