#!/usr/bin/env python3
"""Export the corrected GeneTropica database to static JSON for the React app.

Reproducible build step: reads data/database/genetropica.db (the cleaned,
post-remediation DB) and writes web/public/data/*.json. Re-run whenever the
database changes. Phase 0 emits summary, targets, and drugs.
"""
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "database" / "genetropica.db"
OUT = ROOT / "web" / "public" / "data"

# covalent radii (Angstrom) and AutoDock atom-type -> element, for the binding viewer
COVR = {"C": 0.76, "N": 0.71, "O": 0.66, "S": 1.05, "H": 0.31, "F": 0.57,
        "CL": 1.02, "P": 1.07, "BR": 1.2, "I": 1.39}
ADTYPE = {"A": "C", "C": "C", "N": "N", "NA": "N", "NS": "N", "OA": "O", "OS": "O",
          "O": "O", "SA": "S", "S": "S", "HD": "H", "HS": "H", "H": "H", "F": "F",
          "CL": "CL", "BR": "BR", "P": "P", "I": "I"}


def parse_pose(path):
    """Ligand atoms (element, x, y, z) from MODEL 1 of a Vina pdbqt pose."""
    atoms, inside = [], False
    for ln in Path(path).read_text().splitlines():
        if ln.startswith("MODEL"):
            if inside:
                break
            inside = True
            continue
        if ln.startswith("ENDMDL"):
            break
        if not ln.startswith(("ATOM", "HETATM")) or len(ln) < 54:
            continue
        try:
            x, y, z = float(ln[30:38]), float(ln[38:46]), float(ln[46:54])
        except ValueError:
            continue
        ad = ln.split()[-1].upper()
        atoms.append((ADTYPE.get(ad, ad[:1]), x, y, z))
    return atoms


def infer_bonds(atoms):
    bonds = []
    for i in range(len(atoms)):
        ei, xi, yi, zi = atoms[i]
        for j in range(i + 1, len(atoms)):
            ej, xj, yj, zj = atoms[j]
            if ei == "H" and ej == "H":
                continue
            d = ((xi - xj) ** 2 + (yi - yj) ** 2 + (zi - zj) ** 2) ** 0.5
            if 0.4 < d < COVR.get(ei, 0.77) + COVR.get(ej, 0.77) + 0.45:
                bonds.append([i, j])
    return bonds


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    n_drugs = cur.execute("SELECT COUNT(*) FROM drugs").fetchone()[0]
    n_targets = cur.execute("SELECT COUNT(*) FROM targets").fetchone()[0]
    n_diseases = cur.execute("SELECT COUNT(DISTINCT disease) FROM targets").fetchone()[0]
    n_runs = cur.execute(
        "SELECT COUNT(DISTINCT drug_id || '|' || target_id) FROM docking_results"
    ).fetchone()[0]
    summary = {"drugs": n_drugs, "targets": n_targets, "diseases": n_diseases, "docking_runs": n_runs}
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2))

    targets = [dict(r) for r in cur.execute(
        "SELECT target_id, name, disease, pdb_id, uniprot_id, structure_source, validation_status "
        "FROM targets ORDER BY disease, target_id")]
    (OUT / "targets.json").write_text(json.dumps(targets, indent=2))

    drugs = [{
        "name": r["name"], "category": r["category"], "indication": r["original_indication"],
        "molecular_weight": r["molecular_weight"], "heavy_atoms": r["heavy_atoms"],
        "logp": r["logp"], "inchikey": r["inchikey"], "structure_source": r["structure_source"],
    } for r in cur.execute(
        "SELECT name, category, original_indication, molecular_weight, heavy_atoms, logp, "
        "inchikey, structure_source FROM drugs ORDER BY name")]
    (OUT / "drugs.json").write_text(json.dumps(drugs, indent=2))

    # field.json: per-target drug points for the 3D candidate field
    field = {}
    rows = cur.execute(
        """SELECT m.target_id tid, d.name, d.category, d.original_indication ind,
                  d.molecular_weight mw, d.heavy_atoms ha,
                  m.ligand_efficiency le, m.is_druglike dl, a.overall_pass admet,
                  (SELECT MIN(vina_score) FROM docking_results dr
                   WHERE dr.drug_id=d.drug_id AND dr.target_id=m.target_id) vina
           FROM ml_scores m JOIN drugs d ON d.drug_id=m.drug_id
           LEFT JOIN admet a ON a.drug_id=d.drug_id""").fetchall()
    for r in rows:
        if r["vina"] is None:
            continue
        field.setdefault(r["tid"], []).append({
            "name": r["name"], "category": r["category"], "indication": r["ind"],
            "mw": r["mw"], "ha": r["ha"],
            "le": round(r["le"], 3) if r["le"] is not None else None,
            "vina": round(r["vina"], 2),
            "dl": int(r["dl"] or 0), "admet": int(r["admet"] or 0),
        })
    for tid in field:
        field[tid].sort(key=lambda x: x["vina"])
    (OUT / "field.json").write_text(json.dumps(field, indent=2))

    # admet.json: per-drug ADMET breakdown (risks are 0-1 scores; lipinski/pass are 0/1)
    admet = {r["name"]: {
        "lipinski": r["lipinski_pass"], "hepatotox": r["hepatotoxicity_risk"],
        "herg": r["herg_inhibition_risk"], "bioavail": r["oral_bioavailability"],
        "pass": r["overall_pass"],
    } for r in cur.execute(
        "SELECT d.name, a.lipinski_pass, a.hepatotoxicity_risk, a.herg_inhibition_risk, "
        "a.oral_bioavailability, a.overall_pass FROM admet a JOIN drugs d ON d.drug_id=a.drug_id")}
    (OUT / "admet.json").write_text(json.dumps(admet, indent=2))

    # binding/*.json: per drug-like complex, the docked ligand (atoms + bonds) +
    # FIX-9 predicted contacts. The ligand is centred at the origin for the viewer.
    bind_dir = OUT / "binding"
    bind_dir.mkdir(exist_ok=True)
    drug_id_by_name = {r["name"]: r["drug_id"] for r in cur.execute("SELECT drug_id, name FROM drugs")}
    bind_index, n_bind = {}, 0
    pose_rows = cur.execute(
        """SELECT dr.target_id tid, d.name dname, dr.pose_path pp
           FROM docking_results dr JOIN drugs d ON d.drug_id=dr.drug_id
           JOIN ml_scores m ON m.drug_id=dr.drug_id AND m.target_id=dr.target_id
           WHERE dr.pose_rank=1 AND m.is_druglike=1 AND dr.pose_path IS NOT NULL""").fetchall()
    for r in pose_rows:
        pp = r["pp"]
        path = Path(pp) if Path(pp).is_absolute() else ROOT / pp
        if not path.exists():
            continue
        atoms = parse_pose(path)
        if not atoms:
            continue
        cx = sum(a[1] for a in atoms) / len(atoms)
        cy = sum(a[2] for a in atoms) / len(atoms)
        cz = sum(a[3] for a in atoms) / len(atoms)
        contacts = [{"res": c["residue_name"], "num": c["residue_number"], "chain": c["chain"],
                     "type": c["interaction_type"], "dist": round(c["distance"], 2)}
                    for c in cur.execute(
                        "SELECT residue_name, residue_number, chain, interaction_type, distance "
                        "FROM interactions WHERE drug_id=? AND target_id=? AND pose_rank=1 "
                        "ORDER BY distance", (drug_id_by_name[r["dname"]], r["tid"]))]
        data = {
            "ligand": [{"el": a[0], "x": round(a[1] - cx, 3), "y": round(a[2] - cy, 3), "z": round(a[3] - cz, 3)} for a in atoms],
            "bonds": infer_bonds(atoms),
            "contacts": contacts,
        }
        (bind_dir / f"{r['tid']}__{r['dname']}.json").write_text(json.dumps(data, separators=(",", ":")))
        bind_index.setdefault(r["tid"], []).append(r["dname"])
        n_bind += 1
    for tid in bind_index:
        bind_index[tid].sort()
    (bind_dir / "index.json").write_text(json.dumps(bind_index, indent=2))

    con.close()
    print(f"wrote summary/targets/drugs/field/admet json + {n_bind} binding complexes "
          f"({n_drugs} drugs, {n_targets} targets, {n_runs} runs, "
          f"{sum(len(v) for v in field.values())} field points, {len(admet)} admet)")


if __name__ == "__main__":
    main()
