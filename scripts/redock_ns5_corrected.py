#!/usr/bin/env python3
"""Re-dock the drug-like library against dengue NS5 at the CORRECTED catalytic site.

Why this exists
---------------
The NS5 poses currently on the site were docked into a box centred at
(-118.9, 60.8, 40.2) on 5CCV. The GDD catalytic motif of that structure sits at
residues 662-664 and its nearest atom is 30.0 A from that centre. The box is
25 A wide, so it reaches 12.5 A along an axis and 21.7 A to its farthest corner:
the active site was never inside the search space. Those poses therefore sit in
a region that is not the drug target, and everything derived from them -- the
NS5 Vina ranking and the whole Escape durability page -- describes the wrong
part of the protein.

This script re-docks against the receptor and box that the retrospective
enrichment benchmark already established as correct (see colab/README.md):

    receptor        colab/4V0R_chainA_Mg.pdbqt   chain D, 2.40 A, catalytic Mg2+ kept
    box centre      (-11.3, 19.2, -7.8)          the motif C GDD centroid with the metal
    box size        25 A
    exhaustiveness  8
    seed            42

Checked before this script was written: celecoxib docks in ~5 s at about
-6.9 kcal/mol and its best pose contacts GLY194 / ASP195 / ASP196, the GDD
motif in 4V0R numbering. The old box gave -6.56 against residues 108-114 and
700-703 instead.

NOT bit-for-bit reproducible. --seed fixes Vina's search, but the starting 3D
conformer does not: prepare_ligands.smiles_to_3d calls EmbedMolecule with an
unseeded ETKDGv3 on its primary path (the seeded call is only a fallback for
embedding failures). Repeat runs therefore vary by roughly 0.2 kcal/mol --
celecoxib gave -6.95 and -6.79 on two runs of this script. Ranks near the
middle of the table are not stable to that. To make runs reproducible,
smiles_to_3d needs an optional seed threaded through to EmbedMolecule.

IMPORTANT -- this script does not rebuild escape.json
-----------------------------------------------------
Escape grades a drug by the ConSurf conservation of the residues its pose
touches, and those grades are numbered in the DENV-2 frame. This receptor is
not in that frame, and the offset between them is NOT constant: residues 1-164
are +469, 169-171 are +465, 172-415 are +468. Use the alignment in
data/docking_corrected/4V0R_to_DENV2_map.json, never a flat offset -- a flat
+468 mis-assigns 41% of residues, including 16 of the 48 the poses contact.

Two further things to settle first, both written up in
data/docking_corrected/FINDINGS.md: DENV-2 795 is a tryptophan whose side chain
is unresolved in this crystal and modelled as an ALA stub, yet 28 of 63 poses
contact it and it grades 8 (conserved); and the receptor file holds four chains
plus a stray ligand despite its name, so any residue-number analysis must
filter to chain D first.

A second limit, unchanged by this script: at this corrected site the
retrospective benchmark scored AUC 0.494 (95% CI 0.306-0.684), so the Vina
*scores* still do not separate known NS5 inhibitors from matched decoys. Fixing
the box fixes where the drug is placed, not whether the score can rank drugs.

Output
------
Writes one PDBQT per drug to data/docking_corrected/DENV_NS5/ plus results.json.
It does NOT touch the database, web/public/data, or anything the live site
reads. Running it publishes nothing. About 200 KB total for the full library.

Usage
-----
    python scripts/redock_ns5_corrected.py --smoke     # 1 drug, confirm it works
    python scripts/redock_ns5_corrected.py             # full drug-like band
    python scripts/redock_ns5_corrected.py --jobs 8    # more CPU threads per run
"""
import argparse
import json
import shutil
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.data_acquisition.prepare_ligands import smiles_to_3d, convert_to_pdbqt  # noqa: E402

RECEPTOR = ROOT / "colab" / "4V0R_chainA_Mg.pdbqt"
CENTER = (-11.3, 19.2, -7.8)
BOX = 25
EXHAUSTIVENESS = 8
SEED = 42
NUM_MODES = 3
OUT = ROOT / "data" / "docking_corrected" / "DENV_NS5"
DB = ROOT / "data" / "database" / "genetropica.db"
# The drug-like band the dashboard ranks on, unchanged from the original screen.
MW_MIN, MW_MAX = 250, 600


def drug_like_rows():
    """Drugs in the 250-600 Da band that have a canonical SMILES, by name."""
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    try:
        return con.execute(
            "SELECT name, smiles, molecular_weight mw FROM drugs "
            "WHERE smiles IS NOT NULL AND smiles != '' "
            "AND molecular_weight BETWEEN ? AND ? ORDER BY name",
            (MW_MIN, MW_MAX)).fetchall()
    finally:
        con.close()


def best_score(vina_stdout):
    """The mode-1 affinity from Vina's result table, or None if it printed none."""
    for ln in vina_stdout.splitlines():
        parts = ln.split()
        if len(parts) >= 2 and parts[0] == "1":
            try:
                return float(parts[1])
            except ValueError:
                return None
    return None


def dock(name, smiles, jobs):
    """Prepare the ligand from SMILES and dock it. Returns (score, error)."""
    lig_dir = OUT / "_ligands"
    lig_dir.mkdir(parents=True, exist_ok=True)
    sdf, pdbqt = lig_dir / f"{name}.sdf", lig_dir / f"{name}.pdbqt"
    if not smiles_to_3d(smiles, sdf):
        return None, "3D embedding failed"
    if not convert_to_pdbqt(sdf, pdbqt):
        return None, "pdbqt conversion failed"
    p = subprocess.run([
        "vina", "--receptor", str(RECEPTOR), "--ligand", str(pdbqt),
        "--center_x", str(CENTER[0]), "--center_y", str(CENTER[1]), "--center_z", str(CENTER[2]),
        "--size_x", str(BOX), "--size_y", str(BOX), "--size_z", str(BOX),
        "--exhaustiveness", str(EXHAUSTIVENESS), "--seed", str(SEED),
        "--num_modes", str(NUM_MODES), "--cpu", str(jobs),
        "--out", str(OUT / f"{name}.pdbqt"),
    ], capture_output=True, text=True)
    if p.returncode != 0:
        tail = (p.stderr.strip().splitlines() or ["vina exited non-zero"])[-1]
        return None, tail[:200]
    score = best_score(p.stdout)
    return (score, None) if score is not None else (None, "vina printed no affinity")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--smoke", action="store_true", help="dock one drug and stop")
    ap.add_argument("--jobs", type=int, default=4, help="CPU threads per docking run")
    args = ap.parse_args()

    if not RECEPTOR.exists():
        sys.exit(f"corrected receptor not found: {RECEPTOR}")
    if not DB.exists():
        sys.exit(f"database not found: {DB}")
    if shutil.which("vina") is None:
        sys.exit("vina is not on PATH")
    if shutil.which("obabel") is None:
        sys.exit("obabel is not on PATH (needed for pdbqt conversion)")

    rows = drug_like_rows()
    if not rows:
        sys.exit("no drug-like rows found in the database")
    if args.smoke:
        rows = rows[:1]

    OUT.mkdir(parents=True, exist_ok=True)
    vina_version = subprocess.run(["vina", "--version"], capture_output=True, text=True).stdout.strip()
    print(f"{vina_version}")
    print(f"receptor  {RECEPTOR.relative_to(ROOT)}")
    print(f"box       centre {CENTER}, {BOX} A, exhaustiveness {EXHAUSTIVENESS}, seed {SEED}")
    print(f"docking   {len(rows)} drugs\n")

    results, failed, t0 = {}, [], time.time()
    for i, r in enumerate(rows, 1):
        t = time.time()
        score, err = dock(r["name"], r["smiles"], args.jobs)
        if err:
            failed.append((r["name"], err))
            print(f"  [{i:3d}/{len(rows)}] {r['name']:<26s} FAILED: {err}")
            continue
        results[r["name"]] = {"vina": score, "mw": r["mw"]}
        print(f"  [{i:3d}/{len(rows)}] {r['name']:<26s} {score:>7.2f} kcal/mol  ({time.time()-t:.1f}s)")

    meta = {
        "target": "DENV_NS5",
        "receptor": "4V0R chain A, 2.40 A, catalytic Mg2+ retained",
        "receptor_file": str(RECEPTOR.relative_to(ROOT)),
        "center": list(CENTER),
        "box_size": BOX,
        "exhaustiveness": EXHAUSTIVENESS,
        "seed": SEED,
        "num_modes": NUM_MODES,
        "vina": vina_version,
        "supersedes": (
            "the 5CCV box centred at (-118.9, 60.8, 40.2), whose nearest GDD catalytic "
            "atom was 30.0 A away while the box reached only 21.7 A to its corner"),
        "numbering_warning": (
            "Poses here are in 4V0R chain A numbering (GDD at 194-196). The ConSurf grades "
            "escape.json uses are in the DENV-2 frame 5CCV follows (GDD at 662-664). The "
            "offset is +468 for 390 of 406 shared residues, but 4 percent differ in amino "
            "acid, so the structures are not the same sequence. Map by alignment, not by "
            "assuming the offset, before recomputing any durability score."),
        "ranking_warning": (
            "At this corrected site the retrospective benchmark scored AUC 0.494 "
            "(95 percent CI 0.306-0.684). Correcting the box fixes where a drug is placed, "
            "not whether the Vina score can rank drugs."),
        "n_docked": len(results),
        "n_failed": len(failed),
        "failed": [{"drug": d, "error": e} for d, e in failed],
        "results": results,
    }
    (OUT / "results.json").write_text(json.dumps(meta, indent=2))

    print(f"\n{len(results)} docked, {len(failed)} failed, {time.time() - t0:.0f}s total")
    print(f"poses and results.json -> {OUT.relative_to(ROOT)}")
    print("\nNothing published. Read numbering_warning in results.json before rebuilding escape.json.")


if __name__ == "__main__":
    main()
