#!/usr/bin/env python3
"""Rebuild the NS5 escape/durability leaderboard from the CORRECTED docking poses.

The live escape.json was built from poses docked into a box that never contained
the active site (see data/docking_corrected/FINDINGS.md). This recomputes it from
the corrected poses produced by scripts/redock_ns5_corrected.py.

Methodology is deliberately unchanged from scripts/build_escape.py and
scripts/reanalyze_interactions.py -- the same chemistry-aware contact classifier
(H-bond <=3.5 A polar, hydrophobic <=4.5 A nonpolar C, pi-stacking <=5.5 A
aromatic, ionic <=4.0 A with SMARTS-matched ionizable groups) and the same
durability formula (mean ConSurf grade rescaled 1-9 -> 0-100). Only the poses
change, so any difference in the leaderboard is attributable to the box fix.

Two corrections this script must apply that the original did not need:

  * Numbering. The corrected receptor is not in the DENV-2 frame the ConSurf
    grades use, and the offset is not constant (+469 / +465 / +468 in three
    blocks). Residue numbers are mapped through the pairwise alignment in
    data/docking_corrected/4V0R_to_DENV2_map.json, never by a flat offset.

  * Chain. colab/4V0R_chainA_Mg.pdbqt holds four chains plus a stray ligand
    despite its name. Only chain D is the polymerase, so the receptor is
    filtered to chain D before any distance is measured.

Residue 795 is reported both ways. It is a tryptophan whose side chain is
unresolved in this crystal and modelled as a truncated ALA stub, so poses can
occupy space the real protein fills; it also grades 8 (conserved), which
inflates durability. The script prints the leaderboard computed with it and
without it so the size of that effect is visible rather than assumed.

Writes to data/docking_corrected/. Does NOT touch web/public/data -- publishing
is a separate, deliberate step.
"""
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from reanalyze_interactions import analyze, ionizable, model1  # noqa: E402

POSES = ROOT / "data" / "docking_corrected" / "DENV_NS5"
RECEPTOR = ROOT / "colab" / "4V0R_chainA_Mg.pdbqt"
MAP = ROOT / "data" / "docking_corrected" / "4V0R_to_DENV2_map.json"
CONS = ROOT / "web" / "public" / "data" / "conservation.json"
RESULTS = POSES / "results.json"
DB = ROOT / "data" / "database" / "genetropica.db"
OUT = ROOT / "data" / "docking_corrected"
STUB_RESIDUE = 795          # DENV-2 numbering; unresolved TRP modelled as ALA
RECEPTOR_CHAIN = "D"


def _cls(grade):
    """Same thresholds as scripts/build_escape.py."""
    return "conserved" if grade >= 7 else "variable" if grade <= 3 else "intermediate"


def chain_lines(path, chain):
    return [ln for ln in Path(path).read_text().splitlines()
            if ln.startswith(("ATOM", "HETATM")) and len(ln) > 54 and ln[21] == chain]


def smiles_by_name():
    con = sqlite3.connect(DB)
    try:
        return {n: s for n, s in con.execute(
            "SELECT name, smiles FROM drugs WHERE smiles IS NOT NULL AND smiles != ''")}
    finally:
        con.close()


def build(drug_contacts, grades, key_nums, vina, drop_stub):
    """Assemble the leaderboard exactly as build_escape.py does."""
    drugs, res_drug_count = [], {}
    for name, contacts in sorted(drug_contacts.items()):
        seen = {}
        for c in contacts:
            n = c["denv2"]
            if n in seen or (drop_stub and n == STUB_RESIDUE):
                continue
            g = grades.get(str(n))
            if g is None:
                continue
            seen[n] = {"num": n, "res": c["res"], "grade": g,
                       "cls": _cls(g), "key": n in key_nums, "type": c["type"]}
        rescon = sorted(seen.values(), key=lambda x: x["num"])
        if not rescon:
            continue
        for n in seen:
            res_drug_count[n] = res_drug_count.get(n, 0) + 1
        gl = [r["grade"] for r in rescon]
        mean_g = sum(gl) / len(gl)
        drugs.append({
            "name": name,
            "durability": round((mean_g - 1) / 8 * 100),
            "meanGrade": round(mean_g, 2),
            "nContacts": len(rescon),
            "conserved": sum(1 for r in rescon if r["cls"] == "conserved"),
            "intermediate": sum(1 for r in rescon if r["cls"] == "intermediate"),
            "variable": sum(1 for r in rescon if r["cls"] == "variable"),
            "keyContacts": sum(1 for r in rescon if r["key"]),
            "vina": None if vina.get(name) is None else round(vina[name], 2),
            "dl": 1,
            "contacts": rescon,
        })
    # alphabetical on purpose: the durability ordering these numbers would give is a
    # tie-break, not a finding (see FINDINGS.md), and the page must not imply a winner.
    drugs.sort(key=lambda x: x["name"])
    contacted = [{"num": n, "grade": grades[str(n)], "cls": _cls(grades[str(n)]),
                  "key": n in key_nums, "nDrugs": res_drug_count[n]}
                 for n in sorted(res_drug_count) if str(n) in grades]
    return drugs, contacted


def main():
    for p in (RECEPTOR, MAP, CONS, RESULTS, DB):
        if not p.exists():
            sys.exit(f"missing required input: {p}")

    rec = chain_lines(RECEPTOR, RECEPTOR_CHAIN)
    if not rec:
        sys.exit(f"no chain {RECEPTOR_CHAIN} atoms in {RECEPTOR}")
    m = {int(k): v for k, v in json.loads(MAP.read_text())["map"].items()}
    cons = json.loads(CONS.read_text())
    grades = cons["grades"]
    key_nums = {k["residue_number"] for k in cons.get("key_residues", [])}
    mw = cons.get("mann_whitney", {})
    vina = {k: v["vina"] for k, v in json.loads(RESULTS.read_text())["results"].items()}
    smiles = smiles_by_name()

    print(f"receptor  {RECEPTOR.name} chain {RECEPTOR_CHAIN}, {len(rec)} atoms")
    print(f"poses     {POSES.relative_to(ROOT)}")
    print("contacts  chemistry-aware classifier from reanalyze_interactions.py\n")

    drug_contacts, unmapped, nosmiles = {}, set(), []
    for f in sorted(POSES.glob("*.pdbqt")):
        name = f.stem
        smi = smiles.get(name)
        if smi is None:
            nosmiles.append(name)
            continue
        has_cat, has_an = ionizable(smi)
        out = []
        # analyze() yields (res, num, chain, type, dist) tuples
        for res, num, _chain, ctype, _dist in analyze(rec, model1(f), has_cat, has_an):
            num4 = int(num)
            d2 = m.get(num4)
            if d2 is None:
                unmapped.add(num4)
                continue
            out.append({"denv2": d2, "res": res, "type": ctype})
        drug_contacts[name] = out
    if not any(drug_contacts.values()):
        sys.exit("no contacts detected for any pose -- refusing to write an empty leaderboard")
    print(f"analysed {len(drug_contacts)} poses"
          + (f"; {len(nosmiles)} skipped for missing SMILES" if nosmiles else "")
          + (f"; {len(unmapped)} residue numbers outside the alignment" if unmapped else ""))

    variants = {}
    for drop in (False, True):
        drugs, contacted = build(drug_contacts, grades, key_nums, vina, drop)
        variants["without_795" if drop else "with_795"] = (drugs, contacted)
        tag = "EXCLUDING" if drop else "including"
        print(f"\n--- {tag} residue {STUB_RESIDUE} (the unresolved-side-chain stub)")
        print(f"    {len(drugs)} drugs scored, {len(contacted)} distinct residues contacted")
        for d in drugs[:8]:
            print(f"      {d['name']:<24}{d['durability']:>4}% durable   "
                  f"grade {d['meanGrade']:.2f}/9 over {d['nContacts']} contacts")

    a, b = variants["with_795"][0], variants["without_795"][0]
    ra = {d["name"]: i for i, d in enumerate(a)}
    rb = {d["name"]: i for i, d in enumerate(b)}
    moved = {n: ra[n] - rb[n] for n in ra if n in rb and ra[n] != rb[n]}
    da = {d["name"]: d["durability"] for d in a}
    db_ = {d["name"]: d["durability"] for d in b}
    shifted = {n: da[n] - db_[n] for n in da if n in db_ and da[n] != db_[n]}
    print(f"\n--- effect of the stub residue")
    print(f"    drugs whose durability changes: {len(shifted)} of {len(da)}"
          + (f"  (largest {max(shifted.values(), key=abs):+d} points)" if shifted else ""))
    print(f"    drugs whose rank changes:       {len(moved)}"
          + (f"  (largest {max(moved.values(), key=abs):+d} places)" if moved else ""))
    if a and b:
        print(f"    top drug: {a[0]['name']} ({a[0]['durability']}%) "
              f"-> {b[0]['name']} ({b[0]['durability']}%) when excluded")

    for key, (drugs, contacted) in variants.items():
        payload = {
            "target": "DENV_NS5",
            "bindingMean": mw.get("binding_mean"),
            "nonbindingMean": mw.get("nonbinding_mean"),
            "mwP": mw.get("p_value"),
            "mwSignificant": mw.get("significant"),
            "contacted": contacted,
            "drugs": drugs,
            "provenance": {
                "poses": "corrected catalytic-site docking, 4V0R chain D, box centre (-11.3, 19.2, -7.8)",
                "supersedes": "poses from the 5CCV box whose centre was 30.0 A from the GDD motif",
                "numbering": "mapped to DENV-2 by alignment (4V0R_to_DENV2_map.json); offset is not constant",
                "structure_serotype": "DENV-3 (96.9% identity), scored against DENV-2 ConSurf grades",
                "stub_residue_795": ("excluded" if key == "without_795" else
                                     "included; unresolved TRP side chain modelled as ALA"),
                "ranking_caveat": ("the underlying Vina scores do not discriminate actives from decoys "
                                   "at this site (AUC 0.494, 95% CI 0.306-0.684)"),
                "reproducibility": "ligand conformers are embedded unseeded; repeat runs vary ~0.2 kcal/mol",
            },
        }
        p = OUT / f"escape_corrected_{key}.json"
        p.write_text(json.dumps(payload, indent=1))
        print(f"\nwrote {p.relative_to(ROOT)}")
    print("\nNothing published. web/public/data is untouched.")


if __name__ == "__main__":
    main()
