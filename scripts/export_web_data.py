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

    con.close()
    print(f"wrote {OUT}/summary.json targets.json drugs.json field.json "
          f"({n_drugs} drugs, {n_targets} targets, {n_runs} runs, "
          f"{sum(len(v) for v in field.values())} field points)")


if __name__ == "__main__":
    main()
