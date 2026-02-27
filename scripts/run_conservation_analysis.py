"""Run the full conservation analysis pipeline."""

import json
import logging
import sys
from pathlib import Path

# Ensure project root is importable
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(level=logging.INFO)

from src.conservation.run_alignment import parse_clustal_alignment, compute_pairwise_identity
from src.conservation.conservation_scores import (
    compute_all_entropies,
    normalize_to_consurf_scale,
    compute_binding_site_test,
    extract_key_residue_conservation,
    save_conservation_scores,
    BINDING_SITE_RESIDUES,
)
from src.conservation.map_to_structure import (
    fetch_pdb,
    write_conservation_pdb,
    generate_pymol_script,
)
from src.conservation.conservation_scores import CONSURF_DIR


def main():
    # Load alignment
    aln_path = Path("data/conservation/alignment/alignment.fasta")
    aln_text = aln_path.read_text()
    aligned = parse_clustal_alignment(aln_text)
    names = list(aligned.keys())
    print(f"Loaded alignment: {len(aligned)} sequences, {len(list(aligned.values())[0])} columns")

    # Pairwise identity
    identity = compute_pairwise_identity(aligned)
    print("\nPairwise Identity Matrix:")
    header = f"{'':>8}" + "  ".join(f"{n:>7}" for n in names)
    print(header)
    for n1 in names:
        vals = "  ".join(f"{identity[n1][n2]:>7.1f}" for n2 in names)
        print(f"{n1:>8}  {vals}")

    # Compute entropy and grades
    entropies = compute_all_entropies(aligned)
    grades = normalize_to_consurf_scale(entropies)
    print(f"\nComputed {len(entropies)} position scores")
    print(f"Grade distribution: min={min(grades)}, max={max(grades)}, mean={sum(grades)/len(grades):.1f}")
    grade_counts = {}
    for g in grades:
        grade_counts[g] = grade_counts.get(g, 0) + 1
    print(f"Grade counts: {dict(sorted(grade_counts.items()))}")

    # Save scores
    save_conservation_scores(entropies, grades)

    # Key residue table
    key_residues = [533, 534, 535, 663, 664, 737, 794]
    table = extract_key_residue_conservation(aligned, "DENV-2", key_residues)
    print("\nKey Residue Conservation:")
    for row in table:
        resi = row["residue_number"]
        ref = row["reference_aa"]
        cons = row["conservation_pct"]
        virus_aas = " ".join(f"{v}:{row[v]}" for v in names)
        print(f"  Res {resi} ({ref}): {cons:.0f}% conserved | {virus_aas}")

    # Statistical test
    ref_seq = aligned.get("DENV-2", "")
    resi_to_idx = {}
    resi_num = 0
    for idx, aa in enumerate(ref_seq):
        if aa != "-":
            resi_num += 1
            resi_to_idx[resi_num] = idx

    binding_indices = [resi_to_idx[r] for r in BINDING_SITE_RESIDUES if r in resi_to_idx]
    test_result = compute_binding_site_test(grades, binding_indices)
    print("\nMann-Whitney U Test:")
    print(f"  Binding site mean grade: {test_result['binding_mean']}")
    print(f"  Non-binding mean grade: {test_result['nonbinding_mean']}")
    print(f"  p-value: {test_result['p_value']}")
    print(f"  Significant: {test_result['significant']}")

    # Save analysis results JSON
    results = {
        "pairwise_identity": identity,
        "mann_whitney": test_result,
        "key_residues": table,
    }
    out_path = CONSURF_DIR / "analysis_results.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {out_path}")

    # Generate conservation PDB and PyMOL script
    # Build residue-number → grade map for DENV-2
    grades_by_resi = {}
    resi_num = 0
    for idx, aa in enumerate(ref_seq):
        if aa != "-":
            resi_num += 1
            if idx < len(grades):
                grades_by_resi[resi_num] = grades[idx]

    pdb_text = fetch_pdb("5ZQK")
    if pdb_text:
        write_conservation_pdb(pdb_text, grades_by_resi, CONSURF_DIR / "5ZQK_conservation.pdb")
        print("Conservation PDB written")
    else:
        print("WARNING: Could not fetch PDB 5ZQK")

    generate_pymol_script(
        pdb_path="5ZQK_conservation.pdb",
        output_path=CONSURF_DIR / "conservation_view.pml",
    )
    print("PyMOL script written")

    # Save grades_by_resi for dashboard use
    grades_path = CONSURF_DIR / "grades_by_residue.json"
    with open(grades_path, "w") as f:
        json.dump({str(k): v for k, v in grades_by_resi.items()}, f, indent=2)
    print(f"Grades by residue saved to {grades_path}")


if __name__ == "__main__":
    main()
