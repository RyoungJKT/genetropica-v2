#!/usr/bin/env python3
"""Extract missing interactions for DENV_NS5 and CHIKV_nsP2 drug-target pairs.

These were missed due to DB locking in a previous pipeline run.
Uses retry logic and extended timeout to handle DB contention.
"""

import sqlite3
import sys
import time
from pathlib import Path

# Ensure project root is on the path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.docking.interaction_analysis import analyze_interactions
from src.utils.config import DB_PATH

# --- Configuration ---

BASE_DIR = PROJECT_ROOT
STRUCTURES_DIR = BASE_DIR / "data" / "structures"
DOCKING_RESULTS_DIR = BASE_DIR / "data" / "docking_results"

# Missing DENV_NS5 interactions (18 drugs)
DENV_NS5_DRUGS = [
    "pentoxifylline", "pibrentasvir", "prednisolone", "prochlorperazine",
    "pyrimethamine", "rimantadine", "ruxolitinib", "simeprevir",
    "sorafenib", "stavudine", "sunitinib", "telaprevir",
    "telbivudine", "trifluridine", "umifenovir", "vandetanib",
    "velpatasvir", "voxilaprevir",
]

# Missing CHIKV_nsP2 interactions (7 drugs)
CHIKV_NSP2_DRUGS = [
    "telaprevir", "telbivudine", "trifluridine", "umifenovir",
    "vandetanib", "velpatasvir", "voxilaprevir",
]

TASKS = [
    ("DENV_NS5",   "5CCV", DENV_NS5_DRUGS),
    ("CHIKV_nsP2", "3TRK", CHIKV_NSP2_DRUGS),
]

SLEEP_BETWEEN = 0.5   # seconds between DB writes
DB_TIMEOUT = 30       # seconds to wait for DB lock
MAX_RETRIES = 5
RETRY_DELAY = 2.0     # seconds between retries


def store_interactions_safe(drug_id, target_id, interactions, pose_rank=1):
    """Store interactions with extended timeout and retry logic."""
    for attempt in range(MAX_RETRIES):
        try:
            conn = sqlite3.connect(str(DB_PATH), timeout=DB_TIMEOUT)
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("PRAGMA journal_mode = WAL")
            try:
                conn.execute(
                    "DELETE FROM interactions WHERE drug_id = ? AND target_id = ? AND pose_rank = ?",
                    (drug_id, target_id, pose_rank),
                )
                for inter in interactions:
                    conn.execute(
                        """INSERT INTO interactions
                           (drug_id, target_id, pose_rank, residue_name,
                            residue_number, chain, interaction_type, distance)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            drug_id, target_id, pose_rank,
                            inter["residue_name"], inter["residue_number"],
                            inter["chain"], inter["interaction_type"],
                            inter["distance"],
                        ),
                    )
                conn.commit()
                return True
            finally:
                conn.close()
        except sqlite3.OperationalError as e:
            if "locked" in str(e) and attempt < MAX_RETRIES - 1:
                print(f"    DB locked, retry {attempt + 1}/{MAX_RETRIES} in {RETRY_DELAY}s...")
                time.sleep(RETRY_DELAY)
            else:
                raise
    return False


def main():
    total_pairs = len(DENV_NS5_DRUGS) + len(CHIKV_NSP2_DRUGS)
    processed = 0
    errors = 0

    print(f"Extracting interactions for {total_pairs} missing drug-target pairs")
    print(f"Database: {DB_PATH}")
    print()

    for target_id, pdb_id, drugs in TASKS:
        receptor_path = STRUCTURES_DIR / f"{pdb_id}_clean.pdbqt"

        if not receptor_path.exists():
            print(f"ERROR: Receptor file not found: {receptor_path}")
            errors += len(drugs)
            continue

        print(f"--- {target_id} ({pdb_id}) -- {len(drugs)} drugs ---")

        for drug_id in drugs:
            processed += 1
            ligand_path = (
                DOCKING_RESULTS_DIR / target_id / f"{pdb_id}_clean_{drug_id}_out.pdbqt"
            )

            if not ligand_path.exists():
                print(f"  [{processed}/{total_pairs}] SKIP {drug_id}: ligand file not found")
                errors += 1
                continue

            # Step 1: Analyze interactions (no DB access)
            interactions = analyze_interactions(receptor_path, ligand_path)

            # Step 2: Store in DB with retry logic
            try:
                store_interactions_safe(drug_id, target_id, interactions, pose_rank=1)
                print(
                    f"  [{processed}/{total_pairs}] {drug_id}: "
                    f"{len(interactions)} interactions stored"
                )
            except Exception as e:
                print(f"  [{processed}/{total_pairs}] ERROR {drug_id}: {e}")
                errors += 1

            # Sleep to avoid DB contention
            time.sleep(SLEEP_BETWEEN)

    print()
    print(f"Done. Processed {processed} pairs, {errors} errors.")

    # Verify counts
    conn = sqlite3.connect(str(DB_PATH), timeout=DB_TIMEOUT)
    try:
        for target_id, _, drugs in TASKS:
            for drug_id in drugs:
                row = conn.execute(
                    "SELECT COUNT(*) FROM interactions WHERE drug_id = ? AND target_id = ?",
                    (drug_id, target_id),
                ).fetchone()
                count = row[0] if row else 0
                if count == 0:
                    print(f"  WARNING: {drug_id}/{target_id} has 0 interactions in DB")
    finally:
        conn.close()
    print("Verification complete.")


if __name__ == "__main__":
    main()
