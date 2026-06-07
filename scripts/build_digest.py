#!/usr/bin/env python3
"""Build web/api/_digest.mjs, the compact grounding context for the "ask the data"
assistant (web/api/ask.ts).

Pure read of already-exported web data (summary, targets, field, escape), stdlib
only, so it has no heavy dependencies and is also called at the end of
export_web_data.py once every input (including escape.json) has been written.
Emitted as a .mjs ESM module so the Vercel serverless function can import it
without a JSON import attribute (a bare JSON import crashes the function at load).
"""
import json
from pathlib import Path

CAVEATS = [
    "The ML score is a target-agnostic activity prior (identical for a drug across all targets), not a per-target prediction.",
    "Docking under-ranks the true small-molecule NS5 inhibitors: retrospective AUC 0.37 for NS5, below random.",
    "Only dengue NS5 was retrospectively validated; the other targets have no equivalent test.",
    "Sofosbuvir is included as a known-active positive control, not a discovery.",
    "Drug-like means molecular weight 250-600 Da; the headline ranking uses Vina score plus ligand efficiency over drug-like candidates.",
    "The Escape / Durability tool is a DENV NS5-only heuristic: it scores how conserved the residues each drug's docked pose contacts are (mean ConSurf grade 1-9, mapped to 0-100% durability). It is not an experimental resistance assay, and the binding-site versus rest conservation gap is not statistically significant (Mann-Whitney p approximately 0.07).",
]


def _load(p):
    return json.loads(Path(p).read_text())


def build_digest(out_dir):
    out_dir = Path(out_dir)
    summary = _load(out_dir / "summary.json")
    targets = _load(out_dir / "targets.json")
    field = _load(out_dir / "field.json")

    digest = {
        "summary": summary,
        "targets": [{"id": t["target_id"], "name": t["name"], "disease": t["disease"], "pdb": t["pdb_id"]} for t in targets],
        "topCandidates": {
            tid: [{"name": p["name"], "vina": p["vina"], "le": p["le"], "admetSafe": bool(p["admet"])}
                  for p in sorted([q for q in pts if q["dl"] == 1 and q["le"] is not None], key=lambda q: -q["le"])[:12]]
            for tid, pts in field.items()
        },
        "caveats": list(CAVEATS),
    }

    esc_path = out_dir / "escape.json"
    if esc_path.exists():
        esc = _load(esc_path)
        ds = esc.get("drugs", [])
        digest["escape"] = {
            "target": esc.get("target"),
            "what": ("Per-drug evolutionary escape / durability for DENV NS5, from the Escape tab. "
                     "Durability (0-100%) is the mean ConSurf conservation grade (1 variable, 9 conserved) "
                     "of the residues a drug's docked pose contacts; higher means the virus is less able to "
                     "escape that drug by mutating, because those residues are conserved."),
            "bindingSiteConservationGrade": esc.get("bindingMean"),
            "restOfProteinConservationGrade": esc.get("nonbindingMean"),
            "mannWhitneyP": esc.get("mwP"),
            "mostDurable": [{"name": d["name"], "durability": d["durability"], "meanGrade": d["meanGrade"],
                             "conservedContacts": d["conserved"], "variableContacts": d["variable"], "vina": d["vina"]}
                            for d in ds[:10]],
            "leastDurable": [{"name": d["name"], "durability": d["durability"]} for d in ds[-5:]],
        }
    else:
        digest["caveats"] = [c for c in digest["caveats"] if "Escape / Durability" not in c]

    api_dir = out_dir.parent.parent / "api"
    api_dir.mkdir(parents=True, exist_ok=True)
    (api_dir / "_digest.mjs").write_text("export default " + json.dumps(digest) + "\n")
    return digest


if __name__ == "__main__":
    d = build_digest(Path(__file__).resolve().parents[1] / "web" / "public" / "data")
    print(f"_digest.mjs written: {len(json.dumps(d))} bytes; escape section: {'escape' in d}")
    if "escape" in d:
        top = d["escape"]["mostDurable"][:3]
        print("  most durable:", ", ".join(x["name"] + " " + str(x["durability"]) + "%" for x in top))
