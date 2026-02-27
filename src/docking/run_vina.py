"""AutoDock Vina batch docking runner.

Handles single and batch molecular docking with AutoDock Vina,
storing results (scores + poses) in the database and on disk.
"""

import logging
import subprocess
from pathlib import Path
from typing import Optional

from src.docking.prepare_receptor import SearchBox, define_search_box
from src.utils.config import DOCKING_DIR, LIGANDS_DIR, STRUCTURES_DIR, TARGET_PROTEINS
from src.utils.db import get_connection, init_db

logger = logging.getLogger(__name__)


def dock_single(
    receptor_pdbqt: Path,
    ligand_pdbqt: Path,
    box: SearchBox,
    output_dir: Optional[Path] = None,
    exhaustiveness: int = 8,
    n_poses: int = 3,
) -> Optional[dict]:
    """Run a single AutoDock Vina docking.

    Args:
        receptor_pdbqt: Path to prepared receptor PDBQT.
        ligand_pdbqt: Path to ligand PDBQT.
        box: SearchBox with center and size coordinates.
        output_dir: Directory for output poses. Defaults to DOCKING_DIR.
        exhaustiveness: Vina exhaustiveness parameter.
        n_poses: Number of binding poses to generate.

    Returns:
        Dict with 'output_path', 'scores' (list of floats), and 'log',
        or None on failure.
    """
    out_dir = output_dir or DOCKING_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    stem = f"{receptor_pdbqt.stem}_{ligand_pdbqt.stem}"
    output_path = out_dir / f"{stem}_out.pdbqt"
    log_path = out_dir / f"{stem}.log"

    cmd = [
        "vina",
        "--receptor", str(receptor_pdbqt),
        "--ligand", str(ligand_pdbqt),
        "--center_x", str(box.center_x),
        "--center_y", str(box.center_y),
        "--center_z", str(box.center_z),
        "--size_x", str(box.size_x),
        "--size_y", str(box.size_y),
        "--size_z", str(box.size_z),
        "--exhaustiveness", str(exhaustiveness),
        "--num_modes", str(n_poses),
        "--out", str(output_path),
        "--log", str(log_path),
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

        if result.returncode != 0:
            logger.warning("Vina failed for %s: %s", ligand_pdbqt.name, result.stderr)
            return None

        scores = _parse_vina_log(log_path)
        if not scores:
            scores = _parse_vina_stdout(result.stdout)

        logger.info(
            "Docked %s -> %s: best score %.2f kcal/mol",
            ligand_pdbqt.name, receptor_pdbqt.name,
            scores[0] if scores else float("nan"),
        )

        return {
            "output_path": output_path,
            "scores": scores,
            "log": result.stdout,
        }

    except FileNotFoundError:
        logger.error("AutoDock Vina not found. Install: conda install -c conda-forge autodock-vina")
        return None
    except subprocess.TimeoutExpired:
        logger.warning("Docking timed out for %s", ligand_pdbqt.name)
        return None


def _parse_vina_log(log_path: Path) -> list[float]:
    """Parse Vina log file for binding affinities."""
    scores = []
    if not log_path.exists():
        return scores

    with open(log_path) as f:
        in_table = False
        for line in f:
            if "-----+------------" in line:
                in_table = True
                continue
            if in_table:
                parts = line.split()
                if len(parts) >= 2:
                    try:
                        scores.append(float(parts[1]))
                    except ValueError:
                        if scores:
                            break
    return scores


def _parse_vina_stdout(stdout: str) -> list[float]:
    """Parse Vina stdout for binding affinities (fallback)."""
    scores = []
    in_table = False
    for line in stdout.splitlines():
        if "-----+------------" in line:
            in_table = True
            continue
        if in_table:
            parts = line.split()
            if len(parts) >= 2:
                try:
                    scores.append(float(parts[1]))
                except ValueError:
                    if scores:
                        break
    return scores


def _store_docking_result(
    drug_id: str, target_id: str, scores: list[float],
    output_path: Path, db_path: Optional[Path] = None,
) -> None:
    """Store docking scores in the database."""
    conn = get_connection(db_path)
    try:
        for rank, score in enumerate(scores, start=1):
            conn.execute(
                """INSERT OR REPLACE INTO docking_results
                   (drug_id, target_id, vina_score, pose_rank, pose_path)
                   VALUES (?, ?, ?, ?, ?)""",
                (drug_id, target_id, score, rank, str(output_path)),
            )
        conn.commit()
    finally:
        conn.close()


def dock_batch(
    target_id: str,
    receptor_pdbqt: Path,
    ligand_dir: Optional[Path] = None,
    exhaustiveness: int = 8,
    n_poses: int = 3,
    n_drugs: Optional[int] = None,
) -> dict[str, dict]:
    """Dock all ligands in a directory against a single receptor.

    Args:
        target_id: Target identifier (e.g. 'DENV_NS3').
        receptor_pdbqt: Path to prepared receptor PDBQT.
        ligand_dir: Directory with ligand PDBQT files. Defaults to LIGANDS_DIR.
        exhaustiveness: Vina exhaustiveness parameter.
        n_poses: Number of poses per ligand.
        n_drugs: Limit to first N drugs (for testing).

    Returns:
        Dict mapping drug_id to docking result dict.
    """
    lig_dir = ligand_dir or LIGANDS_DIR
    box = define_search_box(target_id)

    ligands = sorted(lig_dir.glob("*.pdbqt"))
    if n_drugs:
        ligands = ligands[:n_drugs]

    results = {}
    total = len(ligands)

    for i, lig_path in enumerate(ligands, start=1):
        drug_id = lig_path.stem
        logger.info("[%d/%d] Docking %s against %s...", i, total, drug_id, target_id)

        out_dir = DOCKING_DIR / target_id
        result = dock_single(
            receptor_pdbqt, lig_path, box,
            output_dir=out_dir,
            exhaustiveness=exhaustiveness,
            n_poses=n_poses,
        )

        if result and result["scores"]:
            _store_docking_result(
                drug_id, target_id, result["scores"], result["output_path"]
            )
            results[drug_id] = result
        else:
            logger.warning("Skipping %s — docking failed", drug_id)

    logger.info(
        "Batch docking complete for %s: %d/%d successful",
        target_id, len(results), total,
    )
    return results


def dock_all(
    exhaustiveness: int = 8,
    n_poses: int = 3,
    n_drugs: Optional[int] = None,
) -> dict[str, dict[str, dict]]:
    """Run docking for all drugs against all targets.

    This is the full docking campaign: every drug × every target.

    Args:
        exhaustiveness: Vina exhaustiveness parameter.
        n_poses: Number of poses per drug-target pair.
        n_drugs: Limit drugs per target (for testing).

    Returns:
        Nested dict: target_id -> drug_id -> result.
    """
    from src.docking.prepare_receptor import prepare_receptor

    all_results = {}

    for target_id, info in TARGET_PROTEINS.items():
        logger.info("=== Target: %s (%s) ===", target_id, info["name"])

        receptor_pdbqt = prepare_receptor(target_id)
        if receptor_pdbqt is None:
            logger.warning("Skipping %s — receptor preparation failed", target_id)
            continue

        target_results = dock_batch(
            target_id, receptor_pdbqt,
            exhaustiveness=exhaustiveness,
            n_poses=n_poses,
            n_drugs=n_drugs,
        )
        all_results[target_id] = target_results

    logger.info(
        "Full docking campaign complete: %d targets processed",
        len(all_results),
    )
    return all_results
