#!/usr/bin/env python3
"""Export the corrected GeneTropica database to static JSON for the React app.

Reproducible build step: reads data/database/genetropica.db (the cleaned,
post-remediation DB) and writes web/public/data/*.json. Re-run whenever the
database changes. Phase 0 emits summary, targets, and drugs.
"""
import csv
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "database" / "genetropica.db"
OUT = ROOT / "web" / "public" / "data"

import subprocess
import tempfile

from rdkit import Chem
from rdkit.Chem import AllChem
from rdkit import RDLogger

RDLogger.DisableLog("rdApp.*")

AA = {"ALA", "ARG", "ASN", "ASP", "CYS", "GLN", "GLU", "GLY", "HIS", "ILE", "LEU",
      "LYS", "MET", "PHE", "PRO", "SER", "THR", "TRP", "TYR", "VAL"}


def pose_molblock(pose_path, smiles):
    """All-atom, correct-bond-order ligand molblock in the docked pose. Uses the
    canonical SMILES as the chemistry template (RDKit AssignBondOrdersFromTemplate),
    transfers the docked heavy-atom coordinates onto that template, then adds explicit
    hydrogens from its valid valence model. Returns None if it cannot be built cleanly."""
    sdf = tempfile.mktemp(suffix=".sdf")
    subprocess.run(["obabel", str(pose_path), "-O", sdf, "-f", "1", "-l", "1"], capture_output=True)
    pose = Chem.MolFromMolFile(sdf, removeHs=True, sanitize=True)
    ref = Chem.MolFromSmiles(smiles) if smiles else None
    if pose is None or ref is None:
        return None
    try:
        core = AllChem.AssignBondOrdersFromTemplate(ref, pose)
        match = core.GetSubstructMatch(ref)
        if len(match) != ref.GetNumAtoms():
            return None
        cc = core.GetConformer()
        conf = Chem.Conformer(ref.GetNumAtoms())
        for i in range(ref.GetNumAtoms()):
            conf.SetAtomPosition(i, cc.GetAtomPosition(match[i]))
        m = Chem.Mol(ref)
        m.RemoveAllConformers()
        m.AddConformer(conf, assignId=True)
        m = Chem.AddHs(m, addCoords=True)
        return Chem.MolToMolBlock(m)
    except Exception:  # noqa: BLE001
        return None


def trim_pocket(pdb_text, center, radius=22.0):
    """Keep whole protein residues that have any atom within `radius` of `center`."""
    cx, cy, cz = center
    rows, keep = [], set()
    for ln in pdb_text.splitlines():
        if not ln.startswith(("ATOM", "HETATM")) or len(ln) < 54:
            continue
        if ln[17:20].strip() not in AA:
            continue
        try:
            x, y, z = float(ln[30:38]), float(ln[38:46]), float(ln[46:54])
        except ValueError:
            continue
        key = (ln[21], ln[22:26])
        rows.append((key, ln))
        if (x - cx) ** 2 + (y - cy) ** 2 + (z - cz) ** 2 <= radius * radius:
            keep.add(key)
    return "\n".join([ln for key, ln in rows if key in keep] + ["END"])


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
        "smiles": r["smiles"], "drugbank_id": r["drugbank_id"],
        # ml_binding_score is a target-agnostic ligand prior: identical for a drug across every target.
        "ml": round(r["ml"], 3) if r["ml"] is not None else None,
    } for r in cur.execute(
        "SELECT name, category, original_indication, molecular_weight, heavy_atoms, logp, "
        "inchikey, structure_source, smiles, drugbank_id, "
        "(SELECT ml_binding_score FROM ml_scores m WHERE m.drug_id = drugs.drug_id LIMIT 1) ml "
        "FROM drugs ORDER BY name")]
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

    # _digest.json: compact grounding context for the optional "ask the data" assistant (web/api/ask.ts).
    api_dir = ROOT / "web" / "api"
    api_dir.mkdir(parents=True, exist_ok=True)
    digest = {
        "summary": summary,
        "targets": [{"id": t["target_id"], "name": t["name"], "disease": t["disease"], "pdb": t["pdb_id"]} for t in targets],
        "topCandidates": {
            tid: [{"name": p["name"], "vina": p["vina"], "le": p["le"], "admetSafe": bool(p["admet"])}
                  for p in sorted([q for q in pts if q["dl"] == 1 and q["le"] is not None], key=lambda q: -q["le"])[:12]]
            for tid, pts in field.items()
        },
        "caveats": [
            "The ML score is a target-agnostic activity prior (identical for a drug across all targets), not a per-target prediction.",
            "Docking under-ranks the true small-molecule NS5 inhibitors: retrospective AUC 0.37 for NS5, below random.",
            "Only dengue NS5 was retrospectively validated; the other targets have no equivalent test.",
            "Sofosbuvir is included as a known-active positive control, not a discovery.",
            "Drug-like means molecular weight 250-600 Da; the headline ranking uses Vina score plus ligand efficiency over drug-like candidates.",
        ],
    }
    (api_dir / "_digest.json").write_text(json.dumps(digest))

    # admet.json: per-drug ADMET breakdown (risks are 0-1 scores; lipinski/pass are 0/1)
    admet = {r["name"]: {
        "lipinski": r["lipinski_pass"], "hepatotox": r["hepatotoxicity_risk"],
        "herg": r["herg_inhibition_risk"], "bioavail": r["oral_bioavailability"],
        "pass": r["overall_pass"],
    } for r in cur.execute(
        "SELECT d.name, a.lipinski_pass, a.hepatotoxicity_risk, a.herg_inhibition_risk, "
        "a.oral_bioavailability, a.overall_pass FROM admet a JOIN drugs d ON d.drug_id=a.drug_id")}
    (OUT / "admet.json").write_text(json.dumps(admet, indent=2))

    # admet_profiles.json: rich SwissADME-style profiles (drug-likeness filters,
    # BOILED-Egg absorption, structural alerts, descriptors, 0-5 drug-likeness score).
    prof_src = json.loads((ROOT / "data" / "admet" / "profiles.json").read_text())

    def _passed(p, k):
        v = p.get(k)
        return bool(v.get("pass")) if isinstance(v, dict) else bool(v)

    profiles = sorted(({
        "name": p["name"],
        "desc": {"mw": round(p["descriptors"]["mw"], 1), "logp": round(p["descriptors"]["logp"], 2),
                 "tpsa": round(p["descriptors"]["tpsa"], 1), "hbd": p["descriptors"]["hbd"],
                 "hba": p["descriptors"]["hba"], "rot": p["descriptors"]["rotatable_bonds"]},
        "lipinski": _passed(p, "lipinski"), "veber": _passed(p, "veber"),
        "ghose": _passed(p, "ghose"), "egan": _passed(p, "egan"),
        "esol": round(p["esol"], 2), "gi": p["gi_absorption"], "bbb": p["bbb_permeant"],
        "pains": p.get("pains_alerts", []), "brenk": p.get("brenk_alerts", []),
        "dl": p["drug_likeness_score"],
    } for p in prof_src), key=lambda x: x["name"])
    (OUT / "admet_profiles.json").write_text(json.dumps(profiles, indent=2))

    # literature.json: PubMed evidence per drug-target (keyword-mined; evidence tier included
    # so weak keyword hits can be shown as such and never inflate a candidate).
    lit = [{
        "drug": r["drug"], "target": r["target"], "pmid": r["pmid"], "title": r["title"],
        "rel": r["rel"], "conf": round(r["conf"], 2) if r["conf"] is not None else None, "tier": r["tier"],
    } for r in cur.execute(
        "SELECT d.name drug, l.target_id target, l.pmid, "
        "COALESCE(NULLIF(l.canonical_title,''), l.title) title, l.relationship rel, "
        "l.confidence conf, l.evidence_tier tier FROM literature l "
        "JOIN drugs d ON d.drug_id=l.drug_id ORDER BY d.name, l.target_id, l.confidence DESC")]
    # Merge LLM relation-extraction results if scripts/llm_literature.py has been run.
    llm_path = ROOT / "data" / "literature_llm.json"
    if llm_path.exists():
        llm_cache = json.loads(llm_path.read_text())
        for e in lit:
            c = llm_cache.get(f"{e['drug']}|{e['target']}|{e['pmid']}")
            if c:
                e["llm_verdict"] = c.get("verdict")
                e["llm_rel"] = c.get("rel")
                e["llm_conf"] = c.get("conf")
                e["llm_note"] = c.get("note")
    (OUT / "literature.json").write_text(json.dumps(lit, indent=2))

    # binding viewer: a trimmed pocket PDB per target + per drug-like complex an
    # all-atom, bond-order-correct ligand .mol (RDKit) and the FIX-9 predicted contacts.
    bind_dir = OUT / "binding"; bind_dir.mkdir(exist_ok=True)
    struct_dir = OUT.parent / "structures"; struct_dir.mkdir(exist_ok=True)
    grid = {r["target_id"]: (r["grid_center_x"], r["grid_center_y"], r["grid_center_z"])
            for r in cur.execute("SELECT target_id, grid_center_x, grid_center_y, grid_center_z FROM docking_parameters")}
    pdb_by_target = {r["target_id"]: r["pdb_id"] for r in cur.execute("SELECT target_id, pdb_id FROM targets")}
    for tid, center in grid.items():
        recep = ROOT / f"data/structures/{pdb_by_target[tid]}_clean.pdbqt"
        if not recep.exists():
            continue
        tmp = tempfile.mktemp(suffix=".pdb")
        subprocess.run(["obabel", str(recep), "-O", tmp], capture_output=True)
        if Path(tmp).exists():
            (struct_dir / f"{tid}.pdb").write_text(trim_pocket(Path(tmp).read_text(), center))

    drug_id_by_name = {r["name"]: r["drug_id"] for r in cur.execute("SELECT drug_id, name FROM drugs")}
    smiles_by_name = {r["name"]: r["smiles"] for r in cur.execute("SELECT name, smiles FROM drugs")}
    pose_rows = cur.execute(
        """SELECT dr.target_id tid, d.name dname, dr.pose_path pp
           FROM docking_results dr JOIN drugs d ON d.drug_id=dr.drug_id
           JOIN ml_scores m ON m.drug_id=dr.drug_id AND m.target_id=dr.target_id
           WHERE dr.pose_rank=1 AND m.is_druglike=1 AND dr.pose_path IS NOT NULL""").fetchall()
    bind_index, n_bind = {}, 0
    for r in pose_rows:
        pp = r["pp"]
        path = Path(pp) if Path(pp).is_absolute() else ROOT / pp
        if not path.exists():
            continue
        mb = pose_molblock(path, smiles_by_name.get(r["dname"]))
        if mb is None:
            continue
        contacts = [{"res": c["residue_name"], "num": c["residue_number"], "chain": c["chain"],
                     "type": c["interaction_type"], "dist": round(c["distance"], 2)}
                    for c in cur.execute(
                        "SELECT residue_name, residue_number, chain, interaction_type, distance "
                        "FROM interactions WHERE drug_id=? AND target_id=? AND pose_rank=1 "
                        "ORDER BY distance", (drug_id_by_name[r["dname"]], r["tid"])).fetchall()]
        (bind_dir / f"{r['tid']}__{r['dname']}.mol").write_text(mb)
        (bind_dir / f"{r['tid']}__{r['dname']}.json").write_text(json.dumps({"contacts": contacts}, separators=(",", ":")))
        bind_index.setdefault(r["tid"], []).append(r["dname"])
        n_bind += 1
    for tid in bind_index:
        bind_index[tid].sort()
    (bind_dir / "index.json").write_text(json.dumps(bind_index, indent=2))

    # md.json: molecular-dynamics time series + summary (from the FIX-4 / FIX-14 CSVs)
    md_dir = ROOT / "data" / "md_simulation" / "comparison"
    md_drugs = ["celecoxib", "methotrexate", "dasabuvir"]

    def _csv(name):
        with open(md_dir / name) as f:
            return list(csv.DictReader(f))

    def _num(s):
        try:
            return round(float(s), 3)
        except (TypeError, ValueError):
            return None

    md = {"summary": _csv("comparison_summary.csv"), "series": {}}
    for d in md_drugs:
        bp = _csv(f"binding_proxy_{d}.csv")
        md["series"][d] = {
            "rmsd": [[_num(r["time_ns"]), _num(r["protein_rmsd_A"]), _num(r["ligand_rmsd_A"])] for r in _csv(f"rmsd_{d}.csv")],
            "hbonds": [[_num(r["time_ns"]), _num(r["n_hbonds"])] for r in _csv(f"hbonds_{d}.csv")],
            "mindist": [[_num(r["time_ns"]), _num(r["min_dist_A"])] for r in bp],
            "ncontacts": [[_num(r["time_ns"]), _num(r["n_contacts"])] for r in bp],
            "rmsf": [[int(r["resid"]), _num(r["rmsf_A"])] for r in _csv(f"rmsf_{d}.csv")],
            "contacts": [[int(r["resid"]), round(float(r["occupancy_pct"]), 1)] for r in _csv(f"contacts_{d}.csv")[:15]],
        }
    (OUT / "md.json").write_text(json.dumps(md, separators=(",", ":")))

    # conservation.json: ConSurf per-residue grades + cross-flavivirus identity + key residues
    cons = ROOT / "data" / "conservation" / "consurf"
    if (cons / "grades_by_residue.json").exists():
        analysis = json.loads((cons / "analysis_results.json").read_text())
        (OUT / "conservation.json").write_text(json.dumps({
            "grades": json.loads((cons / "grades_by_residue.json").read_text()),
            "identity": analysis.get("pairwise_identity", {}),
            "mann_whitney": analysis.get("mann_whitney", {}),
            "key_residues": analysis.get("key_residues", []),
        }, separators=(",", ":")))

    # validation.json: retrospective ROC + enrichment. The initial small-decoy test was
    # inflated (AUC ~1.0); the honest headline is the fair library-based AUC 0.37 for NS5.
    val_dir = ROOT / "data" / "validation"
    if (val_dir / "validation_summary.json").exists():
        vs = json.loads((val_dir / "validation_summary.json").read_text())

        def _roc(name):
            p = val_dir / f"roc_{name}.csv"
            if not p.exists():
                return []
            with open(p) as f:
                return [[round(float(r["fpr"]), 4), round(float(r["tpr"]), 4)] for r in csv.DictReader(f)]

        (OUT / "validation.json").write_text(json.dumps({
            "auc": {k: vs[k]["auc"] for k in ("docking", "gnn", "consensus") if k in vs},
            "ef": json.loads((val_dir / "enrichment_factors.json").read_text()),
            "roc": {k: _roc(k) for k in ("docking", "gnn", "consensus")},
            "metadata": vs.get("metadata", {}),
            "fair_auc": 0.37,
        }, separators=(",", ":")))

    # methods.json: per-target docking grid (reproducibility)
    tname2 = {r["target_id"]: r["name"] for r in cur.execute("SELECT target_id, name FROM targets")}
    methods = {"docking": [
        {"target_id": r["target_id"], "name": tname2.get(r["target_id"], r["target_id"]),
         "center": [round(r["grid_center_x"], 1), round(r["grid_center_y"], 1), round(r["grid_center_z"], 1)],
         "box": round(r["grid_size_x"]), "exhaustiveness": r["exhaustiveness"], "modes": r["num_modes"], "vina": r["vina_version"]}
        for r in cur.execute("SELECT * FROM docking_parameters").fetchall()]}
    (OUT / "methods.json").write_text(json.dumps(methods, separators=(",", ":")))

    con.close()
    print(f"wrote summary/targets/drugs/field/admet json + {n_bind} binding complexes "
          f"({n_drugs} drugs, {n_targets} targets, {n_runs} runs, "
          f"{sum(len(v) for v in field.values())} field points, {len(admet)} admet)")


if __name__ == "__main__":
    main()
