#!/usr/bin/env python3
"""Build web/api/_digest.mjs, the grounding context for the "ask the data" assistant
(web/api/ask.ts).

A comprehensive but compact picture of the dashboard's data so the assistant can
answer what / how / why questions across every /app tab: an overview, a methods
section (how each result is computed), a tools section (what each tab shows and
why), a glossary, real per-target / MD / validation / conservation / ADMET /
literature / escape aggregates, and the honesty caveats.

Pure read of already-exported web data, stdlib only, so it has no heavy
dependencies and is called at the end of export_web_data.py once every input
(including escape.json) has been written. Emitted as a .mjs ESM module so the
Vercel serverless function can import it without a JSON import attribute.
"""
import json
from collections import Counter
from pathlib import Path

ABOUT = (
    "GeneTropica is a computational drug-repurposing screen by Russell Young (British School Jakarta). "
    "It tests 100 already-approved drugs against 6 protein targets from 3 neglected tropical diseases "
    "(dengue, chikungunya, leptospirosis), to surface existing safe medicines that might be repurposed. "
    "It is an honest in-silico screen and a research demonstration, not a discovery claim, a clinical "
    "result, or medical advice."
)

METHODS = {
    "pipeline": ("Each drug is docked to each target with AutoDock Vina, scored two ways (raw Vina energy "
                 "and ligand efficiency), filtered for drug-likeness and ADMET, given a machine-learning "
                 "activity prior, annotated with predicted binding contacts, and analysed for conservation, "
                 "escape/durability, molecular dynamics and retrospective validation. The tabs follow that "
                 "flow: Diseases, Candidates, Binding, Dynamics, ADMET, Conservation, Escape, Insights, "
                 "Methods, Validation."),
    "docking": ("AutoDock Vina 1.2.7. Each target has its own grid box centred on the known active site "
                "(per-target centre and box size are on the Methods tab); exhaustiveness 8, 3 modes. The "
                "Vina score (kcal/mol) estimates binding energy; more negative means stronger predicted "
                "binding. Docking is a fast approximation, not a measured affinity."),
    "ligandEfficiency": ("Vina score divided by heavy-atom count. Raw Vina favours large molecules; ligand "
                         "efficiency corrects that bias. The headline ranking uses BOTH, over drug-like "
                         "(MW 250-600 Da) candidates only."),
    "ml": ("A scikit-learn RandomForest trained on 166 ChEMBL compounds with measured RdRp activity, using a "
           "2048-bit Morgan fingerprint plus the normalised Vina score; cross-validated AUC 0.875. It is a "
           "TARGET-AGNOSTIC activity prior: the same drug gets the same ML score for every target because the "
           "model never sees the specific pocket. Treat it as one weak prior, not a per-target prediction. "
           "(An earlier version mislabelled it a GNN; it is a RandomForest.)"),
    "binding": ("For each drug-like complex the best docked pose is shown in 3D with chemistry-aware predicted "
                "contacts (hydrogen bond, hydrophobic, pi-stacking, salt bridge, ionic; ionic only when the "
                "ligand carries an opposite-charge group). Contacts are geometric predictions from the docked "
                "pose, not an experimental co-crystal structure; residue numbers follow the deposited PDB."),
    "md": ("50 ns all-atom molecular dynamics (AMBER99SB-ILDN + GAFF2, TIP3P water, 300 K) for three candidates "
           "with DENV NS5 (PDB 5CCV). The ligand starts about 30 Angstrom away in solvent, so these are UNBIASED "
           "ASSOCIATION runs (does the drug find and hold a site?), not bound-pose-stability runs and not binding "
           "free energy (no MM-PBSA). A single 50 ns run is anecdotal."),
    "admet": ("SwissADME-style profiling: drug-likeness rule sets (Lipinski, Veber, Ghose, Egan), BOILED-Egg "
              "gastrointestinal-absorption and blood-brain-barrier prediction, PAINS and Brenk structural alerts, "
              "ESOL solubility, and a 0-5 drug-likeness score. Computational estimates from structure, not clinical data."),
    "conservation": ("ConSurf evolutionary conservation grades (1 variable to 9 conserved) per residue of DENV NS5, "
                     "plus cross-flavivirus sequence identity (DENV-1 to 4, ZIKV, WNV, JEV, YFV, and HCV as a distant "
                     "outlier). Residue-level conservation data exists only for NS5."),
    "escape": ("Durability (Escape tab) is the mean ConSurf conservation grade of the residues a drug's docked pose "
               "contacts, mapped to 0-100%. Gripping conserved residues implies a higher barrier to escape mutation; "
               "gripping variable residues implies easy viral escape. An NS5-only heuristic, not a resistance assay."),
    "validation": ("Retrospective enrichment test on DENV NS5. An initial small-decoy test (8 actives, 78 weak decoys) "
                   "gave a near-perfect, INFLATED AUC. On a fairer library-based test docking scored AUC 0.37 for NS5, "
                   "BELOW RANDOM, because the true small-molecule NS5 inhibitors are nucleoside analogues that dock "
                   "weakly versus large molecules. Only NS5 was validated."),
    "literature": ("PubMed references per drug-target found by keyword mining, graded into evidence tiers. Weak keyword "
                   "hits dominate and count as a hint, not proof. A drug that scores well yet has no real literature is "
                   "a more interesting, genuinely novel lead."),
}

TOOLS = [
    {"tab": "Diseases", "what": "The 3 diseases and their 6 protein targets.", "why": "Frames why these neglected diseases need cheap repurposed drugs."},
    {"tab": "Candidates (Explore)", "what": "Per-target ranking of docked drugs by Vina score and ligand efficiency, with drug-likeness and ADMET flags, plus per-target and per-drug panels.", "why": "The core leaderboard of repurposing candidates."},
    {"tab": "Binding", "what": "The 3D docked pose of a drug-like candidate and the residues it is predicted to contact.", "why": "Shows how a drug sits in the pocket and what it touches."},
    {"tab": "Dynamics (MD)", "what": "50 ns molecular-dynamics association runs for 3 candidates versus NS5 (RMSD, distance, H-bonds, contacts).", "why": "Tests whether a drug spontaneously finds and holds the site."},
    {"tab": "ADMET", "what": "Drug-likeness filters, absorption, structural alerts, solubility and toxicity per drug.", "why": "Is the molecule safe and drug-like enough to pursue."},
    {"tab": "Conservation", "what": "Per-residue conservation of NS5 and cross-virus identity.", "why": "Conserved sites are harder for the virus to mutate away."},
    {"tab": "Escape", "what": "Per-drug durability: how conserved the residues each drug grips are.", "why": "Forecasts which drugs the virus can least easily escape."},
    {"tab": "Insights", "what": "What the ML prior is and is not, and the honest NS5 result.", "why": "Explains the AI component and its limits openly."},
    {"tab": "Methods", "what": "Per-target docking grid parameters and software versions.", "why": "Reproducibility."},
    {"tab": "Validation", "what": "Retrospective ROC and enrichment, inflated initial test versus the fair one.", "why": "Does the method actually pick known-good drugs (honest answer: mixed)."},
]

GLOSSARY = {
    "Vina score": "AutoDock Vina docking energy in kcal/mol; more negative means stronger predicted binding.",
    "ligand efficiency": "binding energy per heavy atom; corrects the docking bias toward large molecules.",
    "drug-like": "molecular weight 250-600 Da; the headline ranking uses only drug-like candidates.",
    "ML score / activity prior": "a RandomForest score, target-agnostic (same for a drug across all targets); a weak prior, not a per-target prediction.",
    "ConSurf grade": "evolutionary conservation from 1 (variable) to 9 (conserved).",
    "durability / escape": "durability = mean conservation grade of a drug's contacted residues; high means the virus can least easily escape it.",
    "AUC": "area under the ROC curve; 0.5 is random, 1.0 is perfect, 0.37 is below random.",
    "enrichment factor": "how many more actives appear in the top X percent than expected by chance.",
    "RMSD": "root-mean-square deviation; how far a structure drifts from a reference during the MD run.",
    "association (MD)": "a ligand that started far away finding and holding the protein.",
    "BOILED-Egg": "a model predicting gastrointestinal absorption and blood-brain-barrier permeation.",
    "PAINS / Brenk": "structural-alert lists for problematic or reactive substructures.",
    "ADMET": "absorption, distribution, metabolism, excretion, toxicity.",
}

CAVEATS = [
    "The ML score is a target-agnostic activity prior (identical for a drug across all targets), not a per-target prediction.",
    "Docking under-ranks the true small-molecule NS5 inhibitors: retrospective AUC 0.37 for NS5, below random.",
    "Only dengue NS5 was retrospectively validated; the other five targets have no equivalent test and are hypothesis-generating only.",
    "Sofosbuvir is included as a known-active positive control, not a discovery.",
    "Drug-like means molecular weight 250-600 Da; the headline ranking uses Vina score plus ligand efficiency over drug-like candidates.",
    "The Escape / Durability tool is a DENV NS5-only heuristic (mean ConSurf grade of contacted residues); it is not an experimental resistance assay, and the binding-site versus rest conservation gap is not statistically significant (Mann-Whitney p approximately 0.07).",
    "Everything here is computational. It is a research demonstration, not a discovery claim, a clinical result, or medical advice.",
]


def _load(p):
    return json.loads(Path(p).read_text())


def _exists(out_dir, name):
    return (out_dir / name).exists()


def build_digest(out_dir):
    out_dir = Path(out_dir)
    summary = _load(out_dir / "summary.json")
    targets = _load(out_dir / "targets.json")
    field = _load(out_dir / "field.json")

    digest = {
        "about": ABOUT,
        "summary": summary,
        "methods": METHODS,
        "tools": TOOLS,
        "glossary": GLOSSARY,
        "diseases": sorted({t["disease"] for t in targets}),
        "targets": [{"id": t["target_id"], "name": t["name"], "disease": t["disease"], "pdb": t["pdb_id"],
                     "validation": t.get("validation_status")} for t in targets],
    }

    # Per-target candidate counts and best candidates (drug-like only)
    per_target = {}
    for tid, pts in field.items():
        dl = [p for p in pts if p.get("dl") == 1]
        le_pts = [p for p in dl if p.get("le") is not None]
        best_vina = min(dl, key=lambda p: p["vina"]) if dl else None
        best_le = max(le_pts, key=lambda p: p["le"]) if le_pts else None
        per_target[tid] = {
            "nCandidates": len(pts),
            "nDruglike": len(dl),
            "bestByVina": {"name": best_vina["name"], "vina": best_vina["vina"]} if best_vina else None,
            "bestByLigandEfficiency": ({"name": best_le["name"], "le": best_le["le"], "vina": best_le["vina"]}
                                       if best_le else None),
        }
    digest["perTarget"] = per_target
    digest["topCandidates"] = {
        tid: [{"name": p["name"], "vina": p["vina"], "le": p["le"], "admetSafe": bool(p["admet"])}
              for p in sorted([q for q in pts if q["dl"] == 1 and q["le"] is not None], key=lambda q: -q["le"])[:10]]
        for tid, pts in field.items()
    }

    # Molecular dynamics summary
    if _exists(out_dir, "md.json"):
        md = _load(out_dir / "md.json")
        digest["molecularDynamics"] = {
            "runs": [{"drug": r.get("Drug"), "associatesAt_ns": r.get("Assoc_ns"),
                      "proteinRMSD_A": r.get("Prot_RMSD_avg"), "ligandRMSD_A": r.get("Lig_RMSD_avg"),
                      "hbonds": r.get("HBonds_avg"), "minDist_A": r.get("MinDist_avg"),
                      "contactResiduesOver50pct": r.get("ContactRes_gt50pct")} for r in md.get("summary", [])],
            "note": ("Celecoxib associates at about 3 ns and holds; methotrexate associates at about 14 ns and "
                     "stays mobile; dasabuvir never forms a stable pose within 50 ns. Unbiased association runs, "
                     "not binding free energy."),
        }

    # Retrospective validation
    if _exists(out_dir, "validation.json"):
        v = _load(out_dir / "validation.json")
        digest["validation"] = {
            "aucInitialInflated": v.get("auc"),
            "fairAUC_NS5": v.get("fair_auc"),
            "enrichmentFactors": v.get("ef"),
            "test": v.get("metadata"),
            "note": ("Running this validation is a mark of rigor, not weakness. GeneTropica benchmarked its "
                     "hardest target (NS5) retrospectively, caught that the initial small-decoy test was inflated, "
                     "and openly reports the fair library-based result (docking AUC 0.37, below random). That low "
                     "value reflects a well-known docking limitation (the genuine NS5 inhibitors are nucleoside "
                     "analogues that dock weakly versus larger molecules), not a flaw in the pipeline. The "
                     "transparent, self-critical handling, plus orthogonal evidence from ligand efficiency, ADMET, "
                     "conservation/escape, MD and literature, is what makes the screen credible; most screens never "
                     "run such a check or quietly drop unfavorable numbers."),
        }

    # Conservation
    if _exists(out_dir, "conservation.json"):
        c = _load(out_dir / "conservation.json")
        mw = c.get("mann_whitney", {})
        digest["conservation"] = {
            "scope": "DENV NS5 only",
            "bindingSiteMeanGrade": mw.get("binding_mean"),
            "restMeanGrade": mw.get("nonbinding_mean"),
            "mannWhitneyP": mw.get("p_value"),
            "significant": mw.get("significant"),
            "nBindingResidues": mw.get("n_binding"),
            "keyResidues": [{"num": k["residue_number"], "aa": k["reference_aa"],
                             "conservationPct": k["conservation_pct"]} for k in c.get("key_residues", [])],
            "crossVirusNote": ("DENV-2 NS5 is roughly 50-73% identical to other flaviviruses (DENV-1/3/4, ZIKV, "
                               "WNV, JEV, YFV) and only about 10% to HCV, which is why sofosbuvir (an HCV drug) is "
                               "a control, not a candidate."),
        }

    # ADMET aggregate (per-drug detail lives in the dashboard; here we summarise)
    if _exists(out_dir, "admet_profiles.json"):
        ap = _load(out_dir / "admet_profiles.json")
        n = len(ap) or 1

        def _truthy(v):
            return str(v).strip().lower() in ("yes", "true", "high", "1")

        digest["admet"] = {
            "nDrugs": len(ap),
            "passLipinski": sum(1 for p in ap if p.get("lipinski")),
            "passVeber": sum(1 for p in ap if p.get("veber")),
            "passGhose": sum(1 for p in ap if p.get("ghose")),
            "passEgan": sum(1 for p in ap if p.get("egan")),
            "highGIabsorption": sum(1 for p in ap if _truthy(p.get("gi"))),
            "bbbPermeant": sum(1 for p in ap if _truthy(p.get("bbb"))),
            "withPAINSalert": sum(1 for p in ap if p.get("pains")),
            "meanDrugLikenessScore_0to5": round(sum(p.get("dl", 0) for p in ap) / n, 2),
        }

    # Literature aggregate
    if _exists(out_dir, "literature.json"):
        lit = _load(out_dir / "literature.json")
        digest["literature"] = {
            "totalReferences": len(lit),
            "byEvidenceTier": dict(Counter(x.get("tier") for x in lit)),
            "byTarget": dict(Counter(x.get("target") for x in lit)),
            "note": ("Keyword-mined PubMed references; the weak_keyword tier dominates and is a hint, not proof. "
                     "Drugs that score well yet have no real literature are the more interesting novel leads."),
        }

    # Escape / durability
    if _exists(out_dir, "escape.json"):
        esc = _load(out_dir / "escape.json")
        ds = esc.get("drugs", [])
        digest["escape"] = {
            "target": esc.get("target"),
            "what": ("Per-drug evolutionary escape / durability for DENV NS5 (the Escape tab). Durability (0-100%) "
                     "is the mean ConSurf conservation grade of the residues a drug's docked pose contacts; higher "
                     "means the virus is less able to escape that drug by mutating, because those residues are conserved."),
            "bindingSiteConservationGrade": esc.get("bindingMean"),
            "restOfProteinConservationGrade": esc.get("nonbindingMean"),
            "mannWhitneyP": esc.get("mwP"),
            "mostDurable": [{"name": d["name"], "durability": d["durability"], "meanGrade": d["meanGrade"],
                             "conservedContacts": d["conserved"], "variableContacts": d["variable"], "vina": d["vina"]}
                            for d in ds[:10]],
            "leastDurable": [{"name": d["name"], "durability": d["durability"]} for d in ds[-5:]],
        }

    digest["assessment"] = {
        "credibility": ("GeneTropica's credibility rests on method and transparency, not on any single score. It "
                        "reports unfavorable results openly, keeps the positive control (sofosbuvir) separate from "
                        "discoveries, triangulates several independent signals, and is framed as hypothesis-generating "
                        "research, which is the honest claim for a computational screen."),
        "strengths": [
            "Breadth: 100 approved drugs docked against 6 targets across 3 neglected tropical diseases.",
            "A transparent dual-metric ranking (Vina score plus ligand efficiency) over drug-like candidates, which avoids either size bias.",
            "Orthogonal evidence per candidate: docking, molecular dynamics, ADMET, conservation and escape/durability, and literature.",
            "A real retrospective validation on the hardest target, with the inflated initial test caught and the honest result reported.",
            "A reproducible data pipeline with openly documented limitations.",
        ],
        "honestLimitations": [
            "Docking under-ranks the true small-molecule NS5 inhibitors (validated AUC 0.37 for NS5).",
            "The ML score is a target-agnostic prior, not a per-target predictor.",
            "Only NS5 was retrospectively validated; the other targets are hypothesis-generating.",
            "Literature links are keyword-mined; the MD runs are short, unbiased association runs (not binding free energy).",
        ],
    }
    digest["caveats"] = list(CAVEATS)

    api_dir = out_dir.parent.parent / "api"
    api_dir.mkdir(parents=True, exist_ok=True)
    (api_dir / "_digest.mjs").write_text("export default " + json.dumps(digest) + "\n")
    return digest


if __name__ == "__main__":
    d = build_digest(Path(__file__).resolve().parents[1] / "web" / "public" / "data")
    print(f"_digest.mjs written: {len(json.dumps(d))} bytes")
    print("  sections:", ", ".join(d.keys()))
