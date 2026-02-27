"""AI insights and scoring dashboard page.

Interactive analysis of scoring methods, ADMET safety profiles,
literature evidence, and methodology explanations.
"""

import sys
from pathlib import Path

import streamlit as st

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
# Target selector (sidebar)
# ─────────────────────────────────────────────────────────────
st.sidebar.header("Analysis Scope")

target_options = []
target_labels = {}
for disease, info in DISEASES.items():
    for tid in info["targets"]:
        target_options.append(tid)
        target_labels[tid] = f"{disease} — {TARGET_PROTEINS[tid]['name']}"

target_id = st.sidebar.selectbox(
    "Protein Target",
    options=target_options,
    format_func=lambda x: target_labels[x],
)
target_info = TARGET_PROTEINS[target_id]

df = get_drugs_for_target(target_id)
if df.empty:
    st.warning("No data found. Please run the mock data generator first.")
    st.code("python scripts/generate_mock_data.py")
    st.stop()

# ─────────────────────────────────────────────────────────────
# Section 1 — Scoring Method Comparison
# ─────────────────────────────────────────────────────────────
st.header("1. Scoring Method Comparison")
st.markdown(
    "Compare AutoDock Vina physics-based docking scores against "
    "DeepChem GNN machine-learning predictions. Points near the "
    "diagonal indicate agreement between methods."
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

if lit_drug_options:
    selected_lit_drug = st.selectbox(
        "Select drug to view references",
        options=lit_drug_options,
        format_func=lambda x: f"{lit_drug_names[x].capitalize()} ({int(df[df['drug_id']==x]['lit_count'].values[0])} refs)",
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

For this project, we dock each of our 50 FDA-approved drugs against
6 protein targets, generating the top 3 poses per drug-target pair.
""")

with st.expander("DeepChem GNN — Machine Learning Rescoring"):
    st.markdown("""
Graph Neural Networks (GNNs) treat molecules as graphs where atoms
are nodes and bonds are edges. DeepChem's pre-trained models learn
complex structure-activity relationships from large datasets of
known drug-target interactions.

**Why use ML alongside Vina?**
- Vina uses physics approximations that can miss important interactions
- GNNs capture patterns from experimental data that physics models cannot
- Combining both methods (consensus scoring) reduces false positives

Our consensus formula: **0.4 x Vina + 0.6 x ML**, where both scores
are normalized to a 0-1 scale before combining.
""")

with st.expander("ADMET Predictions — Safety Profiling"):
    st.markdown("""
ADMET stands for **Absorption, Distribution, Metabolism, Excretion,
and Toxicity** — the key pharmacokinetic properties that determine
whether a drug candidate is safe and effective in humans.

Our pipeline evaluates four safety criteria:

| Property | Method | Pass Threshold |
|----------|--------|---------------|
| **Lipinski's Rule of 5** | Molecular descriptor check | All 4 rules satisfied |
| **Hepatotoxicity** | Random Forest classifier | Risk < 50% |
| **hERG Inhibition** | SVM predictor | Risk < 50% |
| **Oral Bioavailability** | Regression model | Score > 0.5 |

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
