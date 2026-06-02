#!/usr/bin/env python3
"""FIX-9: chemistry-aware re-analysis of protein-ligand interactions.

Re-extracts contacts from the best docked pose (MODEL 1) with a classifier that
checks the ligand's chemistry, not just proximity to a residue:

  - Ionic / salt bridge requires the ligand to carry an ionizable group of the
    OPPOSITE charge to the residue (detected by SMARTS). A neutral ligand with
    no ionizable group therefore shows zero ionic/salt-bridge contacts.
  - Hydrogen bond: polar residue atom (N/O/S) within 3.5 A.
  - Pi-stacking: aromatic residue within 5.5 A.
  - Hydrophobic: nonpolar residue carbon within 4.5 A.

All contacts are predicted from the docked pose (not experimentally observed);
the dashboard/export label them as such and state this detection method.

Run: python scripts/reanalyze_interactions.py
"""
import sqlite3
from pathlib import Path

import numpy as np
from MDAnalysis.lib.distances import distance_array
from rdkit import Chem
from rdkit import RDLogger

RDLogger.DisableLog("rdApp.*")
ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data/database/genetropica.db"
STRUCT = ROOT / "data/structures"

HBOND_MAX, HYDROPHOBIC_MAX, IONIC_MAX, PISTACK_MAX = 3.5, 4.5, 4.0, 5.5
AA = {"ALA","ARG","ASN","ASP","CYS","GLN","GLU","GLY","HIS","ILE","LEU","LYS",
      "MET","PHE","PRO","SER","THR","TRP","TYR","VAL"}
POSITIVE, NEGATIVE = {"ARG","LYS","HIS"}, {"ASP","GLU"}
HBOND = {"ARG","ASN","ASP","GLN","GLU","HIS","LYS","SER","THR","TRP","TYR","CYS"}
HYDROPHOBIC = {"ALA","ILE","LEU","MET","PHE","PRO","TRP","TYR","VAL"}
AROMATIC = {"PHE","TRP","TYR","HIS"}

ANION_SMARTS = [Chem.MolFromSmarts(s) for s in
                ["[CX3](=O)[OX2H1]", "[CX3](=O)[O-]", "[SX4](=O)(=O)[OX2H1]",
                 "[SX4](=O)(=O)[O-]", "[PX4](=O)[OX2H1]", "[PX4](=O)[O-]", "c1[nH]nnn1"]]
# basic nitrogen: exclude amide, sulfonamide, phosphoramide, imine/nitrile, aromatic, anilino
CATION_SMARTS = [Chem.MolFromSmarts(s) for s in
                 ["[NX3;!$(N=*);!$(N#*);!$([NX3][CX3]=[OX1,SX1]);!$([NX3][SX4]);"
                  "!$([NX3][PX4]);!$([NX3][a]);!$([n])]",
                  "[NX4+]",
                  "[NX3][CX3]=[NX2,NX3+]",            # amidine
                  "[NH1,NH2,NH0][CX3](=[NH1,NH2,NX2])[NH1,NH2,NH0]"]]  # guanidine


def ionizable(smiles):
    m = Chem.MolFromSmiles(smiles)
    if m is None:
        return (False, False)
    has_cat = any(p is not None and m.HasSubstructMatch(p) for p in CATION_SMARTS)
    has_an = any(p is not None and m.HasSubstructMatch(p) for p in ANION_SMARTS)
    return (has_cat, has_an)


def parse_atoms(lines, only_aa=False):
    out = []
    for ln in lines:
        if not ln.startswith(("ATOM", "HETATM")) or len(ln) < 54:
            continue
        try:
            x, y, z = float(ln[30:38]), float(ln[38:46]), float(ln[46:54])
        except ValueError:
            continue
        res = ln[17:20].strip()
        if only_aa and res not in AA:
            continue
        out.append({"xyz": (x, y, z), "res": res,
                    "num": ln[22:26].strip(), "chain": ln[21].strip() or "A",
                    "atom": ln[12:16].strip()})
    return out


def model1(path):
    """Return the lines of MODEL 1 (best pose), or all lines if no MODEL records."""
    txt = Path(path).read_text().splitlines()
    if not any(l.startswith("MODEL") for l in txt):
        return txt
    out, inside = [], False
    for l in txt:
        if l.startswith("MODEL"):
            if inside:
                break
            inside = True
            continue
        if l.startswith("ENDMDL"):
            break
        if inside:
            out.append(l)
    return out


def classify(res, dist, atom, has_cat, has_an):
    if dist <= IONIC_MAX:
        if res in POSITIVE and has_an:
            return "Salt Bridge" if dist <= HBOND_MAX else "Ionic"
        if res in NEGATIVE and has_cat:
            return "Salt Bridge" if dist <= HBOND_MAX else "Ionic"
    if dist <= HBOND_MAX and res in HBOND and atom[:1] in ("N", "O", "S"):
        return "Hydrogen Bond"
    if dist <= HYDROPHOBIC_MAX and res in HYDROPHOBIC and atom[:1] == "C":
        return "Hydrophobic"
    if dist <= PISTACK_MAX and res in AROMATIC:
        return "Pi-Stacking"
    return None


def analyze(receptor_lines, ligand_lines, has_cat, has_an):
    rec = parse_atoms(receptor_lines, only_aa=True)
    ligatoms = parse_atoms(ligand_lines)
    if not rec or not ligatoms:
        return []
    rc = np.array([a["xyz"] for a in rec], dtype=np.float32)
    lc = np.array([a["xyz"] for a in ligatoms], dtype=np.float32)
    dmin = distance_array(rc, lc).min(axis=1)  # nearest ligand atom per receptor atom
    seen, res_out = set(), []
    for i in np.argsort(dmin):           # closest first -> dedupe keeps closest atom per residue
        d = float(dmin[i])
        if d > PISTACK_MAX:
            break
        a = rec[i]
        key = (a["res"], a["num"], a["chain"])
        if key in seen:
            continue
        t = classify(a["res"], d, a["atom"], has_cat, has_an)
        if t:
            seen.add(key)
            res_out.append((a["res"], a["num"], a["chain"], t, round(d, 2)))
    return res_out


def main():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    pdb = {r["target_id"]: r["pdb_id"] for r in cur.execute("SELECT target_id, pdb_id FROM targets")}
    drugs = {r["drug_id"]: r["smiles"] for r in cur.execute("SELECT drug_id, smiles FROM drugs")}
    ion_cache = {}
    tasks = cur.execute(
        "SELECT DISTINCT drug_id, target_id, pose_path FROM docking_results WHERE pose_rank=1 AND pose_path IS NOT NULL"
    ).fetchall()
    print(f"re-analyzing {len(tasks)} docked complexes (chemistry-aware)...", flush=True)

    recep_cache = {}
    done, total_int = 0, 0
    for t in tasks:
        did, tid, pose = t["drug_id"], t["target_id"], t["pose_path"]
        if not Path(pose).exists():
            continue
        if tid not in recep_cache:
            rp = STRUCT / f"{pdb[tid]}_clean.pdbqt"
            recep_cache[tid] = rp.read_text().splitlines() if rp.exists() else None
        rec_lines = recep_cache[tid]
        if rec_lines is None:
            continue
        if did not in ion_cache:
            ion_cache[did] = ionizable(drugs.get(did, ""))
        has_cat, has_an = ion_cache[did]
        inter = analyze(rec_lines, model1(pose), has_cat, has_an)
        cur.execute("DELETE FROM interactions WHERE drug_id=? AND target_id=? AND pose_rank=1", (did, tid))
        for res, num, chain, typ, dist in inter:
            cur.execute(
                """INSERT INTO interactions
                   (drug_id, target_id, pose_rank, residue_name, residue_number, chain, interaction_type, distance)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (did, tid, 1, res, num, chain, typ, dist))
        total_int += len(inter)
        done += 1
        if done % 100 == 0:
            con.commit()
            print(f"  {done}/{len(tasks)}", flush=True)
    con.commit()

    print(f"done: {done} complexes, {total_int} interactions stored", flush=True)
    pid = cur.execute("SELECT drug_id FROM drugs WHERE name='pibrentasvir'").fetchone()[0]
    print("pibrentasvir interaction types (should have NO Ionic/Salt Bridge):")
    for r in cur.execute("SELECT interaction_type, COUNT(*) c FROM interactions WHERE drug_id=? GROUP BY interaction_type", (pid,)):
        print(f"   {r['interaction_type']}: {r['c']}")
    nionic = cur.execute("""SELECT COUNT(*) FROM interactions i JOIN drugs d ON d.drug_id=i.drug_id
                            WHERE i.interaction_type IN ('Ionic','Salt Bridge')""").fetchone()[0]
    print(f"total ionic/salt-bridge across all drugs now: {nionic}")
    con.close()


if __name__ == "__main__":
    main()
