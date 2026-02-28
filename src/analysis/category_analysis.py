"""Category-level analysis for the 100-drug library.

Computes mean consensus scores per category per target, populates the
category_stats table, and tests hypotheses about which drug categories
score highest for each target.
"""

import logging
from typing import Optional

from src.utils.db import get_connection

logger = logging.getLogger(__name__)

# Expected bottom-quartile categories (negative controls)
NEGATIVE_CONTROL_CATEGORIES = {"H_Negative_Controls", "Q_More_Negatives"}

# Hypothesised top-scoring categories for RdRp/protease targets
HYPOTHESIS_MAP = {
    "DENV_NS5": ["A_RdRp_Inhibitors", "I_Nucleoside_Analogues"],
    "DENV_NS3": ["C_Protease_Inhibitors", "L_HIV_Protease_Inhibitors"],
    "CHIKV_nsP2": ["C_Protease_Inhibitors", "L_HIV_Protease_Inhibitors"],
}


def compute_category_stats(db_path=None) -> list[dict]:
    """Compute mean scores per category per target and store in DB.

    Joins drugs -> docking_results -> ml_scores to compute:
    - mean_vina_score: average best Vina score per drug
    - mean_ml_score: average ML binding prediction
    - mean_consensus_score: average consensus score

    Returns:
        List of category stat dicts.
    """
    conn = get_connection(db_path)

    # Clear existing stats
    conn.execute("DELETE FROM category_stats")

    # Compute stats: join drugs with docking and pre-computed ML/consensus scores
    # Uses consensus_score from ml_scores (already computed with proper
    # within-target normalization and positive-score exclusion)
    query = """
        INSERT INTO category_stats (category, target_id, mean_vina_score,
                                     mean_ml_score, mean_consensus_score,
                                     drug_count)
        SELECT
            d.category,
            ms.target_id,
            AVG(best_vina) AS mean_vina_score,
            AVG(ms.ml_binding_score) AS mean_ml_score,
            AVG(ms.consensus_score) AS mean_consensus_score,
            COUNT(DISTINCT d.drug_id) AS drug_count
        FROM drugs d
        JOIN ml_scores ms ON d.drug_id = ms.drug_id
        JOIN (
            SELECT drug_id, target_id, MIN(vina_score) AS best_vina
            FROM docking_results
            WHERE pose_rank = 1
            GROUP BY drug_id, target_id
        ) dr ON d.drug_id = dr.drug_id
            AND ms.target_id = dr.target_id
        WHERE d.category IS NOT NULL
        GROUP BY d.category, ms.target_id
    """
    conn.execute(query)
    conn.commit()

    # Read back results
    rows = conn.execute("""
        SELECT category, target_id, mean_vina_score, mean_ml_score,
               mean_consensus_score, drug_count
        FROM category_stats
        ORDER BY target_id, mean_consensus_score DESC
    """).fetchall()

    results = []
    for r in rows:
        results.append({
            "category": r[0],
            "target_id": r[1],
            "mean_vina_score": round(r[2], 3) if r[2] else None,
            "mean_ml_score": round(r[3], 3) if r[3] else None,
            "mean_consensus_score": round(r[4], 4) if r[4] else None,
            "drug_count": r[5],
        })

    logger.info("Computed category stats: %d rows", len(results))
    return results


def verify_negative_controls(db_path=None) -> dict:
    """Verify that negative control drugs rank in bottom quartile.

    Checks that drugs in categories H_Negative_Controls and
    Q_More_Negatives have consensus scores in the bottom 25%
    for each target.

    Returns:
        Dict with verification results per target.
    """
    conn = get_connection(db_path)

    results = {}
    targets = [r[0] for r in conn.execute(
        "SELECT DISTINCT target_id FROM ml_scores"
    ).fetchall()]

    for tid in targets:
        # Get all pre-computed consensus scores for this target, ranked
        all_scores = conn.execute("""
            SELECT d.drug_id, d.category, d.name,
                   ms.consensus_score, ms.consensus_rank
            FROM drugs d
            JOIN ml_scores ms ON d.drug_id = ms.drug_id
                AND ms.target_id = ?
            ORDER BY ms.consensus_score DESC
        """, (tid,)).fetchall()

        n_total = len(all_scores)
        if n_total == 0:
            continue

        bottom_quartile_cutoff = n_total * 3 // 4  # index for bottom 25%

        # Find negative control drugs and their ranks
        neg_controls = []
        for rank, row in enumerate(all_scores):
            drug_id, category, name, consensus, cons_rank = row
            if category in NEGATIVE_CONTROL_CATEGORIES:
                neg_controls.append({
                    "drug_id": drug_id,
                    "name": name,
                    "category": category,
                    "rank": rank + 1,
                    "total": n_total,
                    "consensus": round(consensus, 4),
                    "in_bottom_quartile": rank >= bottom_quartile_cutoff,
                })

        n_in_bottom = sum(1 for nc in neg_controls if nc["in_bottom_quartile"])
        results[tid] = {
            "negative_controls": neg_controls,
            "n_total_drugs": n_total,
            "n_negative_controls": len(neg_controls),
            "n_in_bottom_quartile": n_in_bottom,
            "fraction_in_bottom_quartile": (
                n_in_bottom / len(neg_controls) if neg_controls else 0
            ),
            "pass": n_in_bottom >= len(neg_controls) * 0.5,  # 50%+ in bottom quartile
        }

    return results


def test_category_hypotheses(db_path=None) -> dict:
    """Test hypotheses about which categories score highest.

    Tests whether expected top-scoring categories (e.g., RdRp inhibitors
    for NS5) actually rank in the top 3 categories for each target.

    Returns:
        Dict with hypothesis test results per target.
    """
    conn = get_connection(db_path)

    results = {}
    for tid, expected_cats in HYPOTHESIS_MAP.items():
        # Get top categories by mean consensus for this target
        rows = conn.execute("""
            SELECT category, mean_consensus_score, drug_count
            FROM category_stats
            WHERE target_id = ?
            ORDER BY mean_consensus_score DESC
        """, (tid,)).fetchall()

        if not rows:
            results[tid] = {"status": "no_data"}
            continue

        top_3 = [r[0] for r in rows[:3]]
        all_ranked = [(r[0], round(r[1], 4), r[2]) for r in rows]

        found_in_top3 = [cat for cat in expected_cats if cat in top_3]

        results[tid] = {
            "expected_top_categories": expected_cats,
            "actual_top_3": top_3,
            "found_in_top3": found_in_top3,
            "hypothesis_supported": len(found_in_top3) > 0,
            "full_ranking": [
                {"category": c, "mean_consensus": s, "n_drugs": n}
                for c, s, n in all_ranked
            ],
        }

    return results


def run_full_category_analysis(db_path=None) -> dict:
    """Run all category analyses and print a report.

    Returns:
        Dict with category_stats, negative_controls, and hypotheses.
    """
    logger.info("Computing category statistics ...")
    stats = compute_category_stats(db_path)

    logger.info("Verifying negative controls ...")
    neg_controls = verify_negative_controls(db_path)

    logger.info("Testing category hypotheses ...")
    hypotheses = test_category_hypotheses(db_path)

    # Print report
    print("\n" + "=" * 60)
    print("  CATEGORY ANALYSIS REPORT")
    print("=" * 60)

    # Top categories per target
    targets_seen = {}
    for s in stats:
        tid = s["target_id"]
        if tid not in targets_seen:
            targets_seen[tid] = []
        targets_seen[tid].append(s)

    for tid, cat_stats in sorted(targets_seen.items()):
        print(f"\n  {tid}:")
        print(f"  {'Category':<30} {'Consensus':>10} {'Vina':>8} {'ML':>6} {'N':>4}")
        print("  " + "-" * 58)
        for cs in cat_stats[:5]:  # top 5
            print(
                f"  {cs['category']:<30} "
                f"{cs['mean_consensus_score']:>10.4f} "
                f"{cs['mean_vina_score']:>8.3f} "
                f"{cs['mean_ml_score']:>6.3f} "
                f"{cs['drug_count']:>4}"
            )

    # Negative control verification
    print("\n  NEGATIVE CONTROL VERIFICATION:")
    for tid, nc in sorted(neg_controls.items()):
        status = "PASS" if nc["pass"] else "FAIL"
        pct = nc["fraction_in_bottom_quartile"] * 100
        print(f"  {tid}: {status} ({pct:.0f}% in bottom quartile)")
        for drug in nc["negative_controls"]:
            marker = "OK" if drug["in_bottom_quartile"] else "!!"
            print(
                f"    [{marker}] {drug['name']:<25} "
                f"rank {drug['rank']:>3}/{drug['total']} "
                f"consensus={drug['consensus']:.4f}"
            )

    # Hypothesis tests
    print("\n  HYPOTHESIS TESTS:")
    for tid, ht in sorted(hypotheses.items()):
        if ht.get("status") == "no_data":
            print(f"  {tid}: NO DATA")
            continue
        status = "SUPPORTED" if ht["hypothesis_supported"] else "NOT SUPPORTED"
        print(f"  {tid}: {status}")
        print(f"    Expected: {', '.join(ht['expected_top_categories'])}")
        print(f"    Actual top 3: {', '.join(ht['actual_top_3'])}")

    print("=" * 60 + "\n")

    return {
        "category_stats": stats,
        "negative_controls": neg_controls,
        "hypotheses": hypotheses,
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_full_category_analysis()
