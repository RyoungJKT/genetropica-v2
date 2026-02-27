"""End-to-end pipeline runner for GeneTropica.

Orchestrates the full drug repurposing workflow:
  1. Fetch protein targets (PDB structures)
  2. Predict missing structures (ESMFold / ColabFold)
  3. Prepare drug ligands (SMILES -> PDBQT)
  4. Prepare receptors (clean PDB -> PDBQT)
  5. Run molecular docking (AutoDock Vina)
  6. Parse and rank results
  7. Analyze protein-ligand interactions

Supports mock mode for testing without real docking software.
"""

import argparse
import logging
import random
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.utils.config import DOCKING_DIR, STRUCTURES_DIR, TARGET_PROTEINS
from src.utils.db import get_connection, init_db

logger = logging.getLogger(__name__)


def generate_mock_docking(
    target_id: str,
    n_drugs: int = 5,
    n_poses: int = 3,
    seed: int = 42,
) -> None:
    """Generate mock docking results for testing.

    Creates realistic-looking Vina scores and stores them in the database.

    Args:
        target_id: Target identifier or PDB ID.
        n_drugs: Number of drugs to simulate.
        n_poses: Number of poses per drug.
        seed: Random seed for reproducibility.
    """
    # Resolve PDB ID to target_id if needed
    resolved_target = _resolve_target(target_id)
    if not resolved_target:
        logger.error("Unknown target: %s", target_id)
        return

    rng = random.Random(seed)
    conn = get_connection()

    try:
        # Get drug_ids from the database
        cursor = conn.execute("SELECT drug_id FROM drugs LIMIT ?", (n_drugs,))
        drug_ids = [row[0] for row in cursor.fetchall()]

        if not drug_ids:
            logger.warning("No drugs in database. Run generate_mock_data.py first.")
            return

        for drug_id in drug_ids:
            # Generate realistic Vina scores (-12 to -4 kcal/mol)
            best_score = rng.uniform(-11.0, -4.5)
            for rank in range(1, n_poses + 1):
                score = best_score + (rank - 1) * rng.uniform(0.3, 1.5)
                conn.execute(
                    """INSERT OR REPLACE INTO docking_results
                       (drug_id, target_id, vina_score, pose_rank, pose_path)
                       VALUES (?, ?, ?, ?, ?)""",
                    (drug_id, resolved_target, round(score, 2), rank, "mock"),
                )

        conn.commit()
        logger.info(
            "Generated mock docking: %d drugs x %d poses for %s",
            len(drug_ids), n_poses, resolved_target,
        )
    finally:
        conn.close()


def _resolve_target(identifier: str) -> str | None:
    """Resolve a PDB ID or target_id to a valid target_id."""
    if identifier in TARGET_PROTEINS:
        return identifier

    # Check if it's a PDB ID
    for tid, info in TARGET_PROTEINS.items():
        if info["pdb_id"].upper() == identifier.upper():
            return tid

    return None


def predict_missing_structures(target_id: str | None = None) -> dict[str, Path]:
    """Predict structures for targets lacking experimental PDB files.

    For each target, checks if the experimental structure exists and
    is of sufficient quality. If not, attempts ESMFold prediction
    and validates the result.

    Args:
        target_id: Specific target to predict. None = check all targets.

    Returns:
        Dict mapping target_id to the path of the structure used.
    """
    from src.structure_prediction.esmfold_predict import predict_for_target
    from src.structure_prediction.validate_structure import (
        generate_quality_report,
        is_suitable_for_docking,
    )

    targets = {}
    if target_id:
        resolved = _resolve_target(target_id)
        if resolved:
            targets[resolved] = TARGET_PROTEINS[resolved]
    else:
        targets = TARGET_PROTEINS

    results = {}

    for tid, info in targets.items():
        pdb_id = info["pdb_id"]
        exp_path = STRUCTURES_DIR / f"{pdb_id}.pdb"

        if exp_path.exists():
            logger.info("%s: experimental structure exists (%s)", tid, pdb_id)
            results[tid] = exp_path
            continue

        logger.info("%s: no experimental structure, attempting ESMFold...", tid)
        predicted = predict_for_target(tid)

        if predicted and predicted.exists():
            report = generate_quality_report(predicted)
            if report["suitable_for_docking"]:
                logger.info("%s: ESMFold prediction accepted", tid)
                results[tid] = predicted
            else:
                logger.warning(
                    "%s: ESMFold prediction quality too low — %s",
                    tid, report["recommendation"],
                )
        else:
            logger.warning("%s: structure prediction failed", tid)

    return results


def run_real_pipeline(
    target_id: str | None = None,
    n_drugs: int | None = None,
    exhaustiveness: int = 8,
    predict_structures: bool = False,
) -> None:
    """Run the real docking pipeline.

    Args:
        target_id: Specific target to dock. None = all targets.
        n_drugs: Limit number of drugs. None = all drugs.
        exhaustiveness: Vina exhaustiveness parameter.
        predict_structures: If True, predict missing structures first.
    """
    from src.docking.prepare_receptor import prepare_receptor
    from src.docking.run_vina import dock_batch

    # Optionally predict missing structures
    if predict_structures:
        logger.info("=== Structure Prediction Phase ===")
        predict_missing_structures(target_id)

    targets = {}
    if target_id:
        resolved = _resolve_target(target_id)
        if resolved:
            targets[resolved] = TARGET_PROTEINS[resolved]
        else:
            logger.error("Unknown target: %s", target_id)
            return
    else:
        targets = TARGET_PROTEINS

    for tid, info in targets.items():
        logger.info("=== Processing %s (%s) ===", tid, info["name"])

        # Prepare receptor
        receptor = prepare_receptor(tid)
        if receptor is None:
            logger.warning("Skipping %s — receptor preparation failed", tid)
            continue

        # Run batch docking
        dock_batch(
            tid, receptor,
            exhaustiveness=exhaustiveness,
            n_drugs=n_drugs,
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="GeneTropica docking pipeline runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Mock docking for testing (no Vina required)
  python scripts/run_pipeline.py --mock --target 2VBC --n-drugs 5

  # Mock docking for all targets
  python scripts/run_pipeline.py --mock --n-drugs 10

  # Real docking (requires Vina + Open Babel)
  python scripts/run_pipeline.py --target DENV_NS3 --n-drugs 5

  # Predict missing structures first, then dock
  python scripts/run_pipeline.py --predict-structures --target DENV_NS3

  # Full campaign
  python scripts/run_pipeline.py
        """,
    )

    parser.add_argument(
        "--target",
        type=str,
        default=None,
        help="Target ID (e.g. DENV_NS3) or PDB ID (e.g. 2VBC). Default: all targets.",
    )
    parser.add_argument(
        "--n-drugs",
        type=int,
        default=None,
        help="Limit number of drugs to dock. Default: all.",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Generate mock docking scores (no Vina required).",
    )
    parser.add_argument(
        "--exhaustiveness",
        type=int,
        default=8,
        help="Vina exhaustiveness parameter (default: 8).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for mock data (default: 42).",
    )
    parser.add_argument(
        "--predict-structures",
        action="store_true",
        help="Predict missing structures with ESMFold before docking.",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging.",
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(name)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    init_db()

    if args.mock:
        # Mock mode: generate fake scores
        if args.target:
            resolved = _resolve_target(args.target)
            if resolved:
                generate_mock_docking(
                    resolved, n_drugs=args.n_drugs or 5,
                    seed=args.seed,
                )
            else:
                logger.error("Unknown target: %s", args.target)
                sys.exit(1)
        else:
            for tid in TARGET_PROTEINS:
                generate_mock_docking(
                    tid, n_drugs=args.n_drugs or 5,
                    seed=args.seed,
                )
        print("Mock docking complete.")
    else:
        # Real mode: requires Vina + Open Babel
        run_real_pipeline(
            target_id=args.target,
            n_drugs=args.n_drugs,
            exhaustiveness=args.exhaustiveness,
            predict_structures=args.predict_structures,
        )
        print("Docking pipeline complete.")


if __name__ == "__main__":
    main()
