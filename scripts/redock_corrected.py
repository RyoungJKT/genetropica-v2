#!/usr/bin/env python3
"""Re-dock drugs whose structure was corrected in FIX-1 (drug-like band only).

The truncated structures were what actually got docked, so the affected
drugs' Vina scores are for the wrong molecule. This re-prepares each
corrected drug's ligand from the canonical SMILES and re-docks it against
all six targets, replacing the stale docking_results.

Only drugs now in the drug-like band (MW 250-600) are re-docked: larger
corrected molecules fall outside the candidate band and are flagged
separately (not ranked), and re-docking those huge flexible molecules would
mostly exceed Vina's timeout without affecting any ranking.

Usage:
  python scripts/redock_corrected.py --smoke   # one drug x one target
  python scripts/redock_corrected.py           # full bucket-A x 6 targets
"""
import argparse
import logging
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
logging.basicConfig(level=logging.WARNING)

from src.docking.run_vina import dock_single
from src.docking.prepare_receptor import define_search_box, prepare_receptor
from src.data_acquisition.prepare_ligands import smiles_to_3d, convert_to_pdbqt

DB = ROOT / "data/database/genetropica.db"
BAK = ROOT / "data/database/genetropica.db.bak_pre_fix1"


def changed_druglike():
    con = sqlite3.connect(DB); con.row_factory = sqlite3.Row; cur = con.cursor()
    cur.execute(f"ATTACH '{BAK}' AS old")
    rows = cur.execute(
        """SELECT d.drug_id, d.name, d.smiles, d.molecular_weight mw
           FROM drugs d JOIN old.drugs o ON d.drug_id=o.drug_id
           WHERE d.heavy_atoms != o.heavy_atoms
             AND d.molecular_weight BETWEEN 250 AND 600
           ORDER BY d.name""").fetchall()
    con.close()
    return [dict(r) for r in rows]


def targets():
    con = sqlite3.connect(DB); con.row_factory = sqlite3.Row
    t = [dict(r) for r in con.execute("SELECT target_id, pdb_id FROM targets")]
    con.close()
    return t


def prep_ligand(name, smiles):
    lig = ROOT / "data/ligands"
    sdf = lig / "sdf" / f"{name}.sdf"
    pdbqt = lig / "pdbqt" / f"{name}.pdbqt"
    for p in (sdf, pdbqt):
        if p.exists():
            p.unlink()  # force regeneration from the canonical SMILES
    if not smiles_to_3d(smiles, sdf):
        return None
    if not convert_to_pdbqt(sdf, pdbqt):
        return None
    return pdbqt


def store(drug_id, target_id, scores, pose_path):
    con = sqlite3.connect(DB)
    con.execute("DELETE FROM docking_results WHERE drug_id=? AND target_id=?", (drug_id, target_id))
    for rank, s in enumerate(scores, 1):
        con.execute(
            "INSERT INTO docking_results (drug_id,target_id,vina_score,pose_rank,pose_path) VALUES (?,?,?,?,?)",
            (drug_id, target_id, s, rank, str(pose_path)))
    con.commit(); con.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true")
    a = ap.parse_args()

    drugs = changed_druglike()
    tg = targets()
    if a.smoke:
        drugs = [d for d in drugs if d["name"] == "dasabuvir"] or drugs[:1]
        tg = [t for t in tg if t["target_id"] == "DENV_NS5"]

    print(f"Re-docking {len(drugs)} drugs x {len(tg)} targets = {len(drugs)*len(tg)} dockings", flush=True)
    recep = {t["target_id"]: prepare_receptor(t["target_id"]) for t in tg}
    box = {t["target_id"]: define_search_box(t["target_id"]) for t in tg}

    done, failed = 0, []
    for d in drugs:
        lig = prep_ligand(d["name"], d["smiles"])
        if lig is None:
            failed.append((d["name"], "ligand_prep")); print(f"  PREP FAIL {d['name']}", flush=True); continue
        for t in tg:
            tid = t["target_id"]
            if recep[tid] is None:
                failed.append((d["name"], f"{tid}:no_receptor")); continue
            r = dock_single(recep[tid], lig, box[tid],
                            output_dir=ROOT / "data/docking_results" / tid,
                            exhaustiveness=8, n_poses=3)
            if r and r["scores"]:
                store(d["drug_id"], tid, r["scores"], r["output_path"])
                done += 1
                print(f"  ok {d['name']:18s} x {tid:14s} {r['scores'][0]:.2f}", flush=True)
            else:
                failed.append((d["name"], tid)); print(f"  DOCK FAIL {d['name']} x {tid}", flush=True)
    print(f"\nDONE: {done} dockings stored; {len(failed)} failures: {failed[:30]}", flush=True)


if __name__ == "__main__":
    main()
