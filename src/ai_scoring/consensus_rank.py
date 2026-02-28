"""Combine Vina and ML scores into consensus rankings.

Produces final ranked lists per target, identifies novel discovery
candidates, and generates summary statistics.
"""

import logging
from pathlib import Path
from typing import Optional

import pandas as pd

from src.utils.db import get_connection

logger = logging.getLogger(__name__)


def compute_consensus(
    target_id: str,
    vina_weight: float = 0.4,
    ml_weight: float = 0.6,
    db_path: Optional[Path] = None,
) -> pd.DataFrame:
    """Calculate consensus scores and update rankings for a target.

    Normalizes Vina scores across all drugs for the target, then
    combines with ML scores using the specified weights.

    Args:
        target_id: Target identifier.
        vina_weight: Weight for normalized Vina score.
        ml_weight: Weight for ML binding score.
        db_path: Optional database path override.

    Returns:
        DataFrame with drug_id, vina_score, ml_binding_score,
        consensus_score, and consensus_rank.
    """
    conn = get_connection(db_path)

    try:
        df = pd.read_sql_query(
            """SELECT dr.drug_id, dr.vina_score, ml.ml_binding_score
               FROM docking_results dr
               JOIN ml_scores ml ON dr.drug_id = ml.drug_id
                    AND dr.target_id = ml.target_id
               WHERE dr.target_id = ? AND dr.pose_rank = 1
               ORDER BY dr.drug_id""",
            conn,
            params=(target_id,),
        )

        if df.empty:
            logger.warning("No scores found for %s", target_id)
            return df

        # Exclude positive Vina scores (failed docking) from normalization
        # but keep them in the DataFrame with consensus_score = 0
        valid_mask = df["vina_score"] < 0
        n_excluded = (~valid_mask).sum()
        if n_excluded > 0:
            logger.warning(
                "Excluding %d drugs with positive Vina scores from %s rankings",
                n_excluded, target_id,
            )

        # Normalize Vina scores using only valid (negative) scores
        # Maps most negative score to 1.0 and least negative to 0.0
        valid_scores = df.loc[valid_mask, "vina_score"]
        if len(valid_scores) > 0:
            vina_min = valid_scores.min()
            vina_max = valid_scores.max()
        else:
            vina_min = -10.0
            vina_max = -3.0
        vina_range = vina_max - vina_min

        if vina_range > 0:
            df["vina_norm"] = (df["vina_score"] - vina_max) / -vina_range
        else:
            df["vina_norm"] = 0.5

        # Clamp positive-score drugs to 0.0 normalized
        df.loc[~valid_mask, "vina_norm"] = 0.0

        # Consensus = weighted sum
        df["consensus_score"] = (
            vina_weight * df["vina_norm"] + ml_weight * df["ml_binding_score"]
        ).round(4)

        # Rank by consensus (1 = best)
        df["consensus_rank"] = df["consensus_score"].rank(ascending=False, method="min").astype(int)

        # Update database
        for _, row in df.iterrows():
            conn.execute(
                """UPDATE ml_scores
                   SET consensus_score = ?, consensus_rank = ?
                   WHERE drug_id = ? AND target_id = ?""",
                (row["consensus_score"], int(row["consensus_rank"]),
                 row["drug_id"], target_id),
            )
        conn.commit()

        logger.info(
            "Ranked %d drugs for %s (best consensus: %.4f)",
            len(df), target_id, df["consensus_score"].max(),
        )

        return df[["drug_id", "vina_score", "ml_binding_score",
                    "consensus_score", "consensus_rank"]].sort_values("consensus_rank")

    finally:
        conn.close()


def rank_all_targets(
    vina_weight: float = 0.4,
    ml_weight: float = 0.6,
    db_path: Optional[Path] = None,
) -> dict[str, pd.DataFrame]:
    """Compute consensus rankings for all targets.

    Args:
        vina_weight: Weight for Vina scores.
        ml_weight: Weight for ML scores.
        db_path: Optional database path override.

    Returns:
        Dict mapping target_id to ranked DataFrame.
    """
    from src.utils.config import TARGET_PROTEINS

    results = {}
    for target_id in TARGET_PROTEINS:
        df = compute_consensus(target_id, vina_weight, ml_weight, db_path)
        if not df.empty:
            results[target_id] = df

    logger.info("Ranked %d targets", len(results))
    return results


def get_top_candidates(
    target_id: str,
    n: int = 20,
    db_path: Optional[Path] = None,
) -> pd.DataFrame:
    """Return the top N candidates for a target with all scores.

    Args:
        target_id: Target identifier.
        n: Number of candidates to return.
        db_path: Optional database path override.

    Returns:
        DataFrame with drug details, scores, ADMET status, and lit count.
    """
    conn = get_connection(db_path)
    try:
        df = pd.read_sql_query(
            """SELECT
                   d.drug_id, d.name, d.drugbank_id, d.original_indication,
                   dr.vina_score,
                   ml.ml_binding_score, ml.consensus_score, ml.consensus_rank,
                   a.lipinski_pass, a.overall_pass,
                   COALESCE(lit.cnt, 0) AS literature_count
               FROM drugs d
               JOIN docking_results dr ON d.drug_id = dr.drug_id
                    AND dr.pose_rank = 1
               JOIN ml_scores ml ON d.drug_id = ml.drug_id
                    AND dr.target_id = ml.target_id
               LEFT JOIN admet a ON d.drug_id = a.drug_id
               LEFT JOIN (
                   SELECT drug_id, target_id, COUNT(*) AS cnt
                   FROM literature GROUP BY drug_id, target_id
               ) lit ON d.drug_id = lit.drug_id AND dr.target_id = lit.target_id
               WHERE dr.target_id = ?
               ORDER BY ml.consensus_rank
               LIMIT ?""",
            conn,
            params=(target_id, n),
        )
        return df
    finally:
        conn.close()


def flag_novel_discoveries(
    target_id: str,
    top_n: int = 20,
    db_path: Optional[Path] = None,
) -> pd.DataFrame:
    """Find drugs with strong consensus scores but no literature evidence.

    These represent potential novel repurposing opportunities.

    Args:
        target_id: Target identifier.
        top_n: Consider only top N ranked drugs.
        db_path: Optional database path override.

    Returns:
        DataFrame of novel discovery candidates.
    """
    conn = get_connection(db_path)
    try:
        df = pd.read_sql_query(
            """SELECT
                   d.drug_id, d.name, d.original_indication,
                   ml.consensus_score, ml.consensus_rank,
                   a.overall_pass
               FROM drugs d
               JOIN ml_scores ml ON d.drug_id = ml.drug_id
               LEFT JOIN admet a ON d.drug_id = a.drug_id
               LEFT JOIN literature lit
                   ON d.drug_id = lit.drug_id AND ml.target_id = lit.target_id
               WHERE ml.target_id = ?
                 AND lit.id IS NULL
                 AND ml.consensus_rank <= ?
               ORDER BY ml.consensus_rank""",
            conn,
            params=(target_id, top_n),
        )

        logger.info(
            "Found %d novel discovery candidates for %s (top %d)",
            len(df), target_id, top_n,
        )
        return df

    finally:
        conn.close()
