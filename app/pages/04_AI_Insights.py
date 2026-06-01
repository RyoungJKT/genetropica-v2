"""AI insights and scoring dashboard page.

Interactive analysis of scoring methods, ADMET safety profiles,
literature evidence, and methodology explanations.
"""

import sys
from pathlib import Path

import streamlit as st

st.set_page_config(layout="wide")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.components.charts import (
    admet_overview_bars,
    admet_radar,
    literature_bar,
    novel_discoveries_highlight,
    vina_vs_ml_scatter,
)
from src.utils.config import DISEASES, TARGET_PROTEINS
from src.utils.db import (
    get_drug_admet,
    get_drug_literature,
    get_drugs_for_target,
)

st.title("AI Insights & Analysis")
st.markdown(
    "Explore how our AI scoring pipeline evaluates drug candidates — from "
    "molecular docking to safety profiling and literature validation."
)

# ─────────────────────────────────────────────────────────────
# Target selector (sidebar) — visible list with active highlight
# ─────────────────────────────────────────────────────────────
st.sidebar.header("Analysis Scope")

# Custom CSS to style radio buttons as a clean sidebar navigation list
st.sidebar.markdown("""<style>
/* Hide the radio circle indicators */
div[data-testid="stSidebar"] .stRadio [role="radiogroup"] label > div:first-child {
    display: none !important;
}
/* Style each radio option as a sidebar navigation item */
div[data-testid="stSidebar"] .stRadio [role="radiogroup"] label {
    display: flex !important;
    align-items: center !important;
    padding: 0.55rem 0.85rem !important;
    margin: 0.15rem 0 !important;
    border-radius: 0.45rem !important;
    cursor: pointer !important;
    transition: background-color 0.15s ease !important;
    border-left: 3px solid transparent !important;
    font-size: 0.88rem !important;
}
/* Hover state */
div[data-testid="stSidebar"] .stRadio [role="radiogroup"] label:hover {
    background-color: rgba(151, 166, 195, 0.15) !important;
}
/* Selected / active state — use :has() to detect checked radio input */
div[data-testid="stSidebar"] .stRadio [role="radiogroup"] label:has(input:checked) {
    background-color: rgba(80, 140, 250, 0.15) !important;
    border-left: 3px solid #508cfa !important;
    font-weight: 600 !important;
}
/* Hide the label heading above the radio group */
div[data-testid="stSidebar"] .stRadio > label {
    display: none !important;
}
</style>""", unsafe_allow_html=True)

target_options = []
target_labels = {}
for disease, info in DISEASES.items():
    for tid in info["targets"]:
        target_options.append(tid)
        target_labels[tid] = f"{disease} — {TARGET_PROTEINS[tid]['name']}"

target_id = st.sidebar.radio(
    "Protein Target",
    options=target_options,
    format_func=lambda x: target_labels[x],
    label_visibility="collapsed",
)
target_info = TARGET_PROTEINS[target_id]

df = get_drugs_for_target(target_id)
if df.empty:
    st.warning("No data loaded. Generate demonstration data, or run the real pipeline, to populate the database:")
    st.code("python scripts/generate_mock_data.py")
    st.stop()

# ─────────────────────────────────────────────────────────────
# Section 1 — Scoring Method Comparison
# ─────────────────────────────────────────────────────────────
st.header("1. Scoring Method Comparison")
st.markdown(
    "Compare AutoDock Vina physics-based docking scores against "
    "Random Forest ML predictions. Points near the diagonal "
    "indicate agreement between methods."
)

st.plotly_chart(vina_vs_ml_scatter(target_id), use_container_width=True)

# Quick statistics
n_total = len(df)
n_pass = int(df["overall_pass"].sum())
n_with_lit = int((df["lit_count"] > 0).sum())

s1, s2, s3, s4 = st.columns(4)
with s1:
    st.metric("Total Drugs Screened", n_total)
with s2:
    st.metric("ADMET Pass", n_pass, help="Drugs passing all safety filters")
with s3:
    st.metric("With Literature", n_with_lit, help="Drugs with PubMed references for this target")
with s4:
    corr = df["vina_score"].corr(df["ml_binding_score"])
    st.metric("Vina-ML Correlation", f"{corr:.2f}", help="Pearson correlation between scoring methods")

# ─────────────────────────────────────────────────────────────
# Section 2 — ADMET Safety Dashboard
# ─────────────────────────────────────────────────────────────
st.divider()
st.header("2. ADMET Safety Dashboard")
st.markdown(
    "Safety profiling ensures drug candidates meet pharmacokinetic "
    "requirements. Traffic-light indicators summarize each property."
)

# Overview bars for entire library
st.plotly_chart(admet_overview_bars(), use_container_width=True)

# Traffic-light indicators for top 5 candidates
st.subheader("Top 5 Candidate Safety Profiles")

top5 = df.head(5)
for idx, (_, row) in enumerate(top5.iterrows()):
    drug_id = row["drug_id"]
    drug_name = row["name"].capitalize()
    admet = get_drug_admet(drug_id)

    if admet is None:
        continue

    with st.expander(
        f"{'🟢' if admet['overall_pass'] else '🔴'} "
        f"**{drug_name}** — Rank #{int(row['consensus_rank'])}"
    ):
        lip = admet["lipinski_pass"]
        hep = admet["hepatotoxicity_risk"]
        hep_ok = hep < 0.5
        herg = admet["herg_inhibition_risk"]
        herg_ok = herg < 0.5
        bio = admet["oral_bioavailability"]
        bio_ok = bio >= 0.5
        overall = admet["overall_pass"]

        t1, t2, t3 = st.columns(3)

        with t1:
            st.markdown(f"{'🟢' if lip else '🔴'} **Lipinski** — {'Pass' if lip else 'Fail'}")
            st.markdown(f"{'🟢' if hep_ok else '🔴'} **Hepatotox** — Risk {hep:.0%}")

        with t2:
            st.markdown(f"{'🟢' if herg_ok else '🔴'} **hERG** — Risk {herg:.0%}")
            st.markdown(f"{'🟢' if bio_ok else '🟡'} **Bioavail** — {bio:.0%}")

        with t3:
            st.markdown(f"{'🟢' if overall else '🔴'} **Overall** — {'Pass' if overall else 'Fail'}")

        # Mini radar
        st.plotly_chart(admet_radar(drug_id), use_container_width=True, key=f"admet_radar_{idx}")


# ─────────────────────────────────────────────────────────────
# Section 3 — Literature Evidence
# ─────────────────────────────────────────────────────────────
st.divider()
st.header("3. Literature Evidence")
st.markdown(
    "PubMed references linking each drug to the selected target. "
    "Candidates with strong computational scores but **zero** prior "
    "literature represent potential novel discoveries."
)

lit_col, novel_col = st.columns(2)

with lit_col:
    st.subheader("References per Drug")
    st.plotly_chart(literature_bar(target_id), use_container_width=True)

with novel_col:
    st.subheader("Novel Discovery Candidates")
    st.plotly_chart(novel_discoveries_highlight(target_id), use_container_width=True)

# Detailed literature table for selected drug
st.subheader("Literature Detail")
lit_drug_options = df[df["lit_count"] > 0]["drug_id"].tolist()
lit_drug_names = dict(zip(df["drug_id"], df["name"]))

# CSS to give the literature selectbox a prominent card-like appearance
st.markdown("""<style>
div[data-testid="stMainBlockContainer"] [data-testid="stSelectbox"] > div {
    border: 1px solid rgba(120, 130, 150, 0.35) !important;
    border-radius: 0.55rem !important;
    padding: 0.15rem 0.25rem !important;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08), 0 1px 3px rgba(0, 0, 0, 0.06) !important;
    transition: box-shadow 0.15s ease !important;
}
div[data-testid="stMainBlockContainer"] [data-testid="stSelectbox"] > div:hover {
    box-shadow: 0 4px 14px rgba(0, 0, 0, 0.12), 0 2px 5px rgba(0, 0, 0, 0.08) !important;
}
</style>""", unsafe_allow_html=True)

if lit_drug_options:
    selected_lit_drug = st.selectbox(
        "Select drug to view references",
        options=lit_drug_options,
        format_func=lambda x: f"{lit_drug_names[x].capitalize()} ({int(df[df['drug_id']==x]['lit_count'].values[0])} refs)",
    )

    # Show the selected drug's consensus ranking
    drug_row = df[df["drug_id"] == selected_lit_drug].iloc[0]
    drug_rank = int(drug_row["consensus_rank"])
    drug_display_name = drug_row["name"].capitalize()
    n_total = len(df)

    rank_col, score_col, lit_col2 = st.columns(3)
    with rank_col:
        st.metric(
            "Consensus Rank",
            f"#{drug_rank} / {n_total}",
            help=f"{drug_display_name}'s position among all drugs screened for this target",
        )
    with score_col:
        st.metric(
            "Consensus Score",
            f"{drug_row['consensus_score']:.4f}",
            help="Combined Vina + ML normalised score",
        )
    with lit_col2:
        st.metric(
            "References",
            int(drug_row["lit_count"]),
            help="Number of PubMed references for this drug-target pair",
        )

    lit_df = get_drug_literature(selected_lit_drug, target_id)
    if not lit_df.empty:
        display_lit = lit_df[["pmid", "title", "relationship", "confidence"]].copy()
        display_lit.columns = ["PMID", "Title", "Relationship", "Confidence"]
        display_lit["Relationship"] = display_lit["Relationship"].str.replace("_", " ").str.title()

        st.dataframe(
            display_lit,
            use_container_width=True,
            column_config={
                "Confidence": st.column_config.ProgressColumn(
                    min_value=0, max_value=1, format="%.2f",
                ),
            },
        )
    else:
        st.info("No literature references found for this drug-target pair.")
else:
    st.info("No drugs with literature references for this target.")


# ─────────────────────────────────────────────────────────────
# Section 4 — Methodology Explainer
# ─────────────────────────────────────────────────────────────
st.divider()
st.header("4. Methodology")
st.markdown(
    "Accessible explanations of the AI and computational techniques "
    "powering this drug repurposing pipeline."
)

with st.expander("AutoDock Vina — Physics-Based Molecular Docking"):
    st.markdown("""
AutoDock Vina predicts how strongly a drug molecule binds to a protein
target by simulating physical interactions. It evaluates thousands of
possible orientations (poses) and calculates a binding energy in
kcal/mol — **more negative values indicate stronger binding**.

The scoring function accounts for:
- **Van der Waals forces** — shape complementarity between drug and protein
- **Hydrogen bonds** — directional interactions between polar groups
- **Desolvation** — energy cost of displacing water molecules
- **Torsional penalty** — flexibility cost of the drug molecule

**Pipeline parameters:**
- **Software:** AutoDock Vina v1.2.7
- **Exhaustiveness:** 8 (search thoroughness)
- **Poses:** Top 3 per drug-target pair
- **Grid box:** 25 x 25 x 25 angstrom centered on binding site
- **Receptors:** PDB structures cleaned and converted to PDBQT via Open Babel
- **Ligands:** 3D conformers generated with RDKit ETKDG, optimised with MMFF94/UFF

Each of our 50 FDA-approved drugs was docked against all 6 protein
targets (294 runs total, excluding auranofin which contains a gold
atom unsupported by Vina).
""")

with st.expander("Machine Learning Rescoring"):
    st.markdown("""
A Random Forest classifier trained on RDKit molecular descriptors
rescores each drug-target pair. The model uses 10 physicochemical
features (molecular weight, LogP, TPSA, rotatable bonds, H-bond
donors/acceptors, aromatic rings, heavy atom count, fraction of
sp3 carbons, and Vina docking score) to predict binding likelihood.

**Why use ML alongside Vina?**
- Vina uses physics approximations that can miss important interactions
- ML models capture patterns from descriptor space that physics cannot
- Combining both methods (consensus scoring) reduces false positives

**Consensus formula: 0.4 x Vina + 0.6 x ML**, where both scores
are normalised to a 0-1 scale before combining.

**Validation:** ROC analysis against 8 known DENV NS5 RdRp inhibitors
and 78 property-matched decoys yielded AUC = 1.000 for the consensus
method, with enrichment factor EF@1% = 10.8x (maximum possible).
""")

with st.expander("ADMET Predictions — Safety Profiling"):
    st.markdown("""
ADMET stands for **Absorption, Distribution, Metabolism, Excretion,
and Toxicity** — the key pharmacokinetic properties that determine
whether a drug candidate is safe and effective in humans.

Our pipeline evaluates four safety criteria using RDKit molecular
descriptors computed directly from each drug's SMILES structure:

| Property | Method | Pass Threshold |
|----------|--------|---------------|
| **Lipinski's Rule of 5** | MW, LogP, HBD, HBA from RDKit | ≤ 1 violation |
| **Hepatotoxicity** | Descriptor heuristics (MW, LogP, TPSA, reactive groups) | Risk < 50% |
| **hERG Inhibition** | LogP + basic nitrogens + aromatic ring count | Risk < 50% |
| **Oral Bioavailability** | Veber's rules (TPSA, rotatable bonds, LogP) | Score ≥ 0.5 |

A drug must pass **all four** criteria to receive an overall ADMET pass.
Since we use existing FDA-approved drugs, most already have favorable
ADMET profiles — but repurposing for a new indication may reveal
different safety considerations.
""")

with st.expander("PubMedBERT NLP — Literature Mining"):
    st.markdown("""
We use NLP (Natural Language Processing) to search PubMed for existing
evidence linking our drug candidates to the target diseases. This helps
distinguish between:

- **Known connections** — drugs already studied for this indication
  (validates computational predictions)
- **Novel discoveries** — computationally promising drugs with no prior
  literature (potential new repurposing opportunities)

The pipeline queries PubMed using drug names and disease terms, then
uses text classification to categorize the relationship type
(therapeutic, mechanistic, adverse, etc.) and assigns a confidence
score based on the strength of the evidence.
""")

st.divider()
st.caption(
    "GeneTropica v2 — AI Insights | Russell Young, British School Jakarta"
)
