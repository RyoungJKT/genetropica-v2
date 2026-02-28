"""Dock new drugs (those without docking results) against all 6 targets.

Uses AutoDock Vina via dock_single() and stores results directly to the DB.
Prints progress every 20 docking runs and reports final counts.

Uses WAL journal mode and a 30-second timeout to handle concurrent DB access
from other processes (Streamlit app, literature mining, etc.).
"""

import sys
import logging
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")

import sqlite3
from src.docking.run_vina import dock_single
from src.docking.prepare_receptor import define_search_box, prepare_receptor
from src.utils.config import TARGET_PROTEINS, STRUCTURES_DIR, LIGANDS_DIR, DOCKING_DIR, DB_PATH

DB_FILE = str(DB_PATH)


def get_db():
    """Get a DB connection with 60s timeout for concurrent access."""
    conn = sqlite3.connect(DB_FILE, timeout=60)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def store_docking_result(drug_id, target_id, scores, output_path):
    """Store docking scores in the database with retry logic."""
    for attempt in range(3):
        try:
            conn = get_db()
            try:
                for rank, score in enumerate(scores, start=1):
                    conn.execute(
                        """INSERT OR REPLACE INTO docking_results
                           (drug_id, target_id, vina_score, pose_rank, pose_path)
                           VALUES (?, ?, ?, ?, ?)""",
                        (drug_id, target_id, score, rank, str(output_path)),
                    )
                conn.commit()
                return True
            finally:
                conn.close()
        except sqlite3.OperationalError as e:
            if "locked" in str(e) and attempt < 2:
                logging.warning("DB locked, retrying in 5s (attempt %d)...", attempt + 1)
                time.sleep(5)
            else:
                raise
    return False


# Get new drug IDs (those without docking results)
conn = get_db()
new_drug_ids = [r[0] for r in conn.execute("""
    SELECT drug_id FROM drugs
    WHERE drug_id NOT IN (SELECT DISTINCT drug_id FROM docking_results)
""").fetchall()]
conn.close()

print(f"New drugs to dock: {len(new_drug_ids)}")
print(f"Targets: {len(TARGET_PROTEINS)}")
print(f"Expected docking runs: ~{len(new_drug_ids) * len(TARGET_PROTEINS)}")
print()

total, success, fail, skip = 0, 0, 0, 0
start_time = time.time()

for target_id, info in TARGET_PROTEINS.items():
    pdb_id = info["pdb_id"]
    print(f"\n=== Target: {target_id} ({info['name']}, PDB: {pdb_id}) ===")

    receptor = prepare_receptor(target_id)
    if receptor is None:
        print(f"ERROR: Could not prepare receptor for {target_id}")
        continue

    box = define_search_box(target_id)
    out_dir = DOCKING_DIR / target_id
    out_dir.mkdir(parents=True, exist_ok=True)

    target_success = 0
    for i, drug_id in enumerate(new_drug_ids, 1):
        ligand = LIGANDS_DIR / "pdbqt" / f"{drug_id}.pdbqt"
        if not ligand.exists():
            skip += 1
            continue

        total += 1
        result = dock_single(receptor, ligand, box, out_dir, exhaustiveness=8, n_poses=3)
        if result and result["scores"]:
            store_docking_result(drug_id, target_id, result["scores"], result["output_path"])
            success += 1
            target_success += 1
        else:
            fail += 1
            print(f"  FAILED: {drug_id} x {target_id}")

        if total % 20 == 0:
            elapsed = time.time() - start_time
            rate = total / elapsed * 60 if elapsed > 0 else 0
            remaining = (len(new_drug_ids) * 6 - total) / rate if rate > 0 else 0
            print(f"  Progress: {total} docked ({success} ok, {fail} fail), {rate:.1f}/min, ~{remaining:.0f} min remaining")

    print(f"Completed {target_id}: {target_success}/{len(new_drug_ids)} successful")

elapsed = time.time() - start_time
print(f"\n=== DOCKING COMPLETE ===")
print(f"Total runs: {total}")
print(f"Successful: {success}")
print(f"Failed: {fail}")
print(f"Skipped (no PDBQT): {skip}")
print(f"Time: {elapsed/60:.1f} minutes")

# Verify totals with a fresh connection
conn = get_db()
total_pairs = conn.execute(
    "SELECT COUNT(DISTINCT drug_id || '|' || target_id) FROM docking_results WHERE pose_rank = 1"
).fetchone()[0]
print(f"\nTotal drug-target pairs in DB: {total_pairs}")
for tid in TARGET_PROTEINS:
    n = conn.execute(
        "SELECT COUNT(DISTINCT drug_id) FROM docking_results WHERE target_id = ? AND pose_rank = 1",
        (tid,),
    ).fetchone()[0]
    print(f"  {tid}: {n} drugs")

conn.close()
