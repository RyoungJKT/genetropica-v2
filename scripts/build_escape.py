#!/usr/bin/env python3
"""Compute escape.json: per-drug evolutionary escape / durability for DENV NS5.

A docked drug that contacts highly conserved residues has a high barrier to
resistance (the virus cannot easily mutate those positions without paying a
fitness cost), so it is "durable". A drug whose contacts sit on variable
residues is easy for the virus to escape. The durability score is the mean
ConSurf conservation grade (1 = variable, 9 = conserved) of the residues the
drug's best pose actually contacts, mapped to 0-100.

This is a pure read of already-exported web data (conservation.json grades +
binding/<target>__<drug>.json predicted contacts + field.json scores), so it
has no heavy dependencies and is also called at the end of export_web_data.py
to keep the artifact reproducible. Conservation grades exist only for DENV NS5,
so the analysis is scoped to that target and labelled as such in the UI.
"""
import glob
import json
from pathlib import Path

TARGET = "DENV_NS5"


def _cls(grade):
    return "conserved" if grade >= 7 else "variable" if grade <= 3 else "intermediate"


def build_escape(out_dir):
    out_dir = Path(out_dir)
    cons_path = out_dir / "conservation.json"
    if not cons_path.exists():
        return None
    cons = json.loads(cons_path.read_text())
    grades = cons.get("grades", {})
    if not grades:
        return None
    key_nums = {k["residue_number"] for k in cons.get("key_residues", [])}
    mw = cons.get("mann_whitney", {})

    field_path = out_dir / "field.json"
    ns5_field = {}
    if field_path.exists():
        ns5_field = {p["name"]: p for p in json.loads(field_path.read_text()).get(TARGET, [])}

    drugs = []
    res_drug_count = {}
    prefix = f"{TARGET}__"
    for f in sorted(glob.glob(str(out_dir / "binding" / f"{prefix}*.json"))):
        name = Path(f).name[len(prefix):-len(".json")]
        contacts = json.loads(Path(f).read_text()).get("contacts", [])
        seen = {}
        for c in contacts:
            n = c.get("num")
            if n in seen:
                continue
            g = grades.get(str(n))
            if g is None:
                continue
            seen[n] = {"num": n, "res": c.get("res"), "grade": g, "cls": _cls(g), "key": n in key_nums}
        rescon = sorted(seen.values(), key=lambda x: x["num"])
        if not rescon:
            continue
        for n in seen:
            res_drug_count[n] = res_drug_count.get(n, 0) + 1
        gl = [r["grade"] for r in rescon]
        mean_g = sum(gl) / len(gl)
        fld = ns5_field.get(name, {})
        drugs.append({
            "name": name,
            "durability": round((mean_g - 1) / 8 * 100),
            "meanGrade": round(mean_g, 2),
            "nContacts": len(rescon),
            "conserved": sum(1 for r in rescon if r["cls"] == "conserved"),
            "intermediate": sum(1 for r in rescon if r["cls"] == "intermediate"),
            "variable": sum(1 for r in rescon if r["cls"] == "variable"),
            "keyContacts": sum(1 for r in rescon if r["key"]),
            "vina": fld.get("vina"),
            "dl": fld.get("dl", 1),
            "contacts": rescon,
        })
    drugs.sort(key=lambda x: (-x["durability"], x["vina"] if x["vina"] is not None else 0))

    contacted = []
    for n in sorted(res_drug_count):
        g = grades.get(str(n))
        if g is None:
            continue
        contacted.append({"num": n, "grade": g, "cls": _cls(g), "key": n in key_nums, "nDrugs": res_drug_count[n]})

    escape = {
        "target": TARGET,
        "bindingMean": mw.get("binding_mean"),
        "nonbindingMean": mw.get("nonbinding_mean"),
        "mwP": mw.get("p_value"),
        "mwSignificant": mw.get("significant"),
        "contacted": contacted,
        "drugs": drugs,
    }
    (out_dir / "escape.json").write_text(json.dumps(escape, separators=(",", ":")))
    return escape


if __name__ == "__main__":
    e = build_escape(Path(__file__).resolve().parents[1] / "web" / "public" / "data")
    if e and e["drugs"]:
        top = e["drugs"][0]
        print(f"escape.json: {len(e['drugs'])} NS5 drugs, {len(e['contacted'])} contacted residues; "
              f"most durable {top['durability']}% ({top['name']}), least {e['drugs'][-1]['durability']}%")
    else:
        print("escape.json: skipped (no conservation grades found)")
