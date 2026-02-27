"""Extract docking scores and poses from Vina output.

Parses PDBQT output files, ranks results across a campaign,
and builds summary tables for downstream scoring.
"""

import logging
import re
from pathlib import Path
from typing import Optional

import pandas as pd

from src.utils.config import DOCKING_DIR
from src.utils.db import get_connection

logger = logging.getLogger(__name__)


def parse_vina_output(pdbqt_path: Path) -> list[dict]:
    """Parse a Vina output PDBQT file to extract poses and scores.

    Each MODEL block in the output file corresponds to one binding pose.

    Args:
        pdbqt_path: Path to the Vina output PDBQT.

    Returns:
        List of dicts with 'pose_rank', 'vina_score', and 'atoms' (list of lines).
    """
    if not pdbqt_path.exists():
        logger.warning("Output file not found: %s", pdbqt_path)
        return []

    poses = []
    current_pose = None
    current_atoms = []

    with open(pdbqt_path) as f:
        for line in f:
            if line.startswith("MODEL"):
                parts = line.split()
                rank = int(parts[1]) if len(parts) > 1 else len(poses) + 1
                current_pose = {"pose_rank": rank, "vina_score": None, "atoms": []}
                current_atoms = []

            elif line.startswith("REMARK VINA RESULT:"):
                match = re.search(r"RESULT:\s+([-\d.]+)", line)
                if match and current_pose is not None:
                    current_pose["vina_score"] = float(match.group(1))

            elif line.startswith(("ATOM", "HETATM")):
                if current_pose is not None:
                    current_atoms.append(line.rstrip())

            elif line.startswith("ENDMDL"):
                if current_pose is not None:
                    current_pose["atoms"] = current_atoms
                    poses.append(current_pose)
                    current_pose = None
                    current_atoms = []

    return poses


def extract_best_pose(pdbqt_path: Path, output_path: Optional[Path] = None) -> Optional[Path]:
    """Extract the top-ranked pose from a Vina output file.

    Args:
        pdbqt_path: Path to multi-pose Vina output.
        output_path: Where to save the best pose. Defaults to <name>_best.pdbqt.

    Returns:
        Path to the extracted best pose file, or None if parsing fails.
    """
    poses = parse_vina_output(pdbqt_path)
    if not poses:
        return None

    best = min(poses, key=lambda p: p["vina_score"] or 0.0)

    if output_path is None:
        output_path = pdbqt_path.with_name(
            pdbqt_path.stem.replace("_out", "_best") + ".pdbqt"
        )

    with open(output_path, "w") as f:
        for atom_line in best["atoms"]:
            f.write(atom_line + "\n")

    logger.info("Extracted best pose (%.2f kcal/mol) -> %s", best["vina_score"], output_path.name)
    return output_path


def rank_results(target_id: str, db_path: Optional[Path] = None) -> pd.DataFrame:
    """Rank all docking results for a target by Vina score.

    Args:
        target_id: Target identifier.
        db_path: Optional database path override.

    Returns:
        DataFrame sorted by vina_score (best first), with columns:
        drug_id, vina_score, pose_rank.
    """
    conn = get_connection(db_path)
    try:
        df = pd.read_sql_query(
            """SELECT drug_id, vina_score, pose_rank
               FROM docking_results
               WHERE target_id = ? AND pose_rank = 1
               ORDER BY vina_score ASC""",
            conn,
            params=(target_id,),
        )
        return df
    finally:
        conn.close()


def summarize_campaign(db_path: Optional[Path] = None) -> pd.DataFrame:
    """Summarize docking results across all targets.

    Returns a DataFrame with one row per target showing:
    - target_id, n_docked (count), best_score, worst_score, mean_score

    Args:
        db_path: Optional database path override.

    Returns:
        Summary DataFrame.
    """
    conn = get_connection(db_path)
    try:
        df = pd.read_sql_query(
            """SELECT
                   target_id,
                   COUNT(DISTINCT drug_id) AS n_docked,
                   MIN(vina_score) AS best_score,
                   MAX(vina_score) AS worst_score,
                   ROUND(AVG(vina_score), 2) AS mean_score
               FROM docking_results
               WHERE pose_rank = 1
               GROUP BY target_id
               ORDER BY target_id""",
            conn,
        )
        return df
    finally:
        conn.close()


def collect_output_files(
    results_dir: Optional[Path] = None,
) -> dict[str, list[Path]]:
    """Scan the docking results directory and group output files by target.

    Args:
        results_dir: Root docking results directory. Defaults to DOCKING_DIR.

    Returns:
        Dict mapping target_id to list of output PDBQT paths.
    """
    root = results_dir or DOCKING_DIR
    grouped = {}

    if not root.exists():
        return grouped

    for target_dir in sorted(root.iterdir()):
        if target_dir.is_dir():
            files = sorted(target_dir.glob("*_out.pdbqt"))
            if files:
                grouped[target_dir.name] = files

    return grouped
