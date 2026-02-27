"""Conservation scoring using Shannon entropy and statistical analysis.

Computes per-position Shannon entropy from a multiple sequence alignment,
normalizes to a ConSurf-like 1-9 scale, and runs a Mann-Whitney U test
comparing binding site conservation to the rest of the protein.
"""

import logging
import math
from collections import Counter
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from scipy import stats

from src.utils.config import BASE_DIR

logger = logging.getLogger(__name__)

CONSURF_DIR: Path = BASE_DIR / "data" / "conservation" / "consurf"

# Key binding site residues in 5ZQK (NS5 RdRp domain numbering)
BINDING_SITE_RESIDUES = [533, 663, 664, 737, 794]

# GDD catalytic motif residues
GDD_MOTIF_RESIDUES = [533, 534, 535]  # Asp-Gly-Asp in DENV-2 NS5


def compute_shannon_entropy(column: list[str]) -> float:
    """Compute Shannon entropy for an alignment column.

    H(i) = -Σ p(a) × log₂(p(a))

    Lower entropy = more conserved.
    Gaps are excluded from the calculation.

    Args:
        column: List of amino acid characters at one alignment position.

    Returns:
        Shannon entropy value (0.0 = fully conserved).
    """
    residues = [r for r in column if r != "-" and r != "."]
    if not residues:
        return 0.0

    n = len(residues)
    counts = Counter(residues)
    entropy = 0.0

    for count in counts.values():
        p = count / n
        if p > 0:
            entropy -= p * math.log2(p)

    return round(entropy, 4)


def compute_all_entropies(aligned_seqs: dict[str, str]) -> list[float]:
    """Compute Shannon entropy at every alignment position.

    Args:
        aligned_seqs: Dict mapping name to aligned sequence (with gaps).

    Returns:
        List of entropy values, one per alignment column.
    """
    seqs = list(aligned_seqs.values())
    if not seqs:
        return []

    aln_len = len(seqs[0])
    entropies: list[float] = []

    for pos in range(aln_len):
        column = [s[pos] for s in seqs if pos < len(s)]
        entropies.append(compute_shannon_entropy(column))

    return entropies


def normalize_to_consurf_scale(entropies: list[float]) -> list[int]:
    """Normalize Shannon entropy values to ConSurf 1-9 scale.

    Grade 9 = most conserved (entropy ≈ 0)
    Grade 1 = most variable (highest entropy)

    Args:
        entropies: List of Shannon entropy values.

    Returns:
        List of integer grades 1-9.
    """
    if not entropies:
        return []

    max_entropy = max(entropies) if max(entropies) > 0 else 1.0

    grades: list[int] = []
    for h in entropies:
        # Invert: low entropy → high grade
        normalized = 1.0 - (h / max_entropy) if max_entropy > 0 else 1.0
        grade = int(round(normalized * 8)) + 1  # Map to 1-9
        grade = max(1, min(9, grade))
        grades.append(grade)

    return grades


def compute_binding_site_test(
    conservation_grades: list[int],
    binding_site_indices: list[int],
) -> dict:
    """Mann-Whitney U test: binding site vs non-binding residues.

    Tests whether binding site residues are significantly more conserved
    than the rest of the protein.

    Args:
        conservation_grades: ConSurf grades (1-9) for each residue.
        binding_site_indices: Indices of binding site residues in the list.

    Returns:
        Dict with p_value, statistic, binding_mean, nonbinding_mean, significant.
    """
    grades_arr = np.array(conservation_grades)
    binding_mask = np.zeros(len(grades_arr), dtype=bool)

    for idx in binding_site_indices:
        if 0 <= idx < len(grades_arr):
            binding_mask[idx] = True

    binding_scores = grades_arr[binding_mask]
    nonbinding_scores = grades_arr[~binding_mask]

    if len(binding_scores) == 0 or len(nonbinding_scores) == 0:
        return {
            "p_value": 1.0,
            "statistic": 0.0,
            "binding_mean": 0.0,
            "nonbinding_mean": 0.0,
            "n_binding": 0,
            "n_nonbinding": 0,
            "significant": False,
        }

    # One-sided: binding > non-binding (greater conservation)
    stat, p_value = stats.mannwhitneyu(
        binding_scores,
        nonbinding_scores,
        alternative="greater",
    )

    return {
        "p_value": round(float(p_value), 6),
        "statistic": round(float(stat), 2),
        "binding_mean": round(float(binding_scores.mean()), 2),
        "nonbinding_mean": round(float(nonbinding_scores.mean()), 2),
        "n_binding": int(len(binding_scores)),
        "n_nonbinding": int(len(nonbinding_scores)),
        "significant": bool(p_value < 0.05),
    }


def extract_key_residue_conservation(
    aligned_seqs: dict[str, str],
    reference_name: str,
    key_residues: list[int],
) -> list[dict]:
    """Extract conservation data for key residues across all viruses.

    Maps reference sequence residue numbers to alignment positions,
    then extracts the amino acid at that position for each virus.

    Args:
        aligned_seqs: Dict mapping virus name to aligned sequence.
        reference_name: Name of the reference sequence (e.g. 'DENV-2').
        key_residues: Residue numbers in the reference NS5 sequence.

    Returns:
        List of dicts with residue info and per-virus amino acids.
    """
    if reference_name not in aligned_seqs:
        logger.warning("Reference %s not in alignment", reference_name)
        return []

    ref_seq = aligned_seqs[reference_name]
    virus_names = list(aligned_seqs.keys())

    # Build map: reference residue number → alignment position
    ref_pos = 0  # 1-based residue counter (non-gap)
    resi_to_aln: dict[int, int] = {}
    for aln_pos, aa in enumerate(ref_seq):
        if aa != "-":
            ref_pos += 1
            resi_to_aln[ref_pos] = aln_pos

    rows: list[dict] = []
    for resi in key_residues:
        aln_pos = resi_to_aln.get(resi)
        if aln_pos is None:
            continue

        row: dict = {"residue_number": resi, "reference_aa": ref_seq[aln_pos]}
        for virus in virus_names:
            seq = aligned_seqs[virus]
            row[virus] = seq[aln_pos] if aln_pos < len(seq) else "-"

        # Conservation: count how many viruses have same AA as reference
        ref_aa = row["reference_aa"]
        matching = sum(1 for v in virus_names if row[v] == ref_aa)
        row["conservation_pct"] = round(matching / len(virus_names) * 100, 1)

        rows.append(row)

    return rows


def save_conservation_scores(
    entropies: list[float],
    grades: list[int],
    output_dir: Optional[Path] = None,
) -> Path:
    """Save conservation scores to CSV.

    Args:
        entropies: Shannon entropy values per position.
        grades: ConSurf grades (1-9) per position.
        output_dir: Output directory. Defaults to CONSURF_DIR.

    Returns:
        Path to saved CSV file.
    """
    out = output_dir or CONSURF_DIR
    out.mkdir(parents=True, exist_ok=True)

    df = pd.DataFrame({
        "position": list(range(1, len(entropies) + 1)),
        "shannon_entropy": entropies,
        "consurf_grade": grades,
    })

    path = out / "conservation_scores.csv"
    df.to_csv(path, index=False)
    logger.info("Conservation scores saved to %s", path)
    return path
