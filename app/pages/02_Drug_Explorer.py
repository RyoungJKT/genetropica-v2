"""Drug Candidate Explorer dashboard page.

Browse and filter all screened drug candidates with interactive charts
and a detailed drug profile panel.
"""

import sys
from pathlib import Path

import streamlit as st

st.set_page_config(layout="wide")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.components.charts import (
    admet_radar,
    score_comparison_bar,
    score_distribution_histogram,
    top_candidates_bar,
)
from app.components.filters import (
    render_admet_filter,
    render_score_filter,
    render_sort_selector,
    render_target_filter,
)
from src.utils.config import TARGET_PROTEINS
from src.utils.db import get_drug_details, get_drug_literature, get_drugs_for_target

# ─────────────────────────────────────────────────────────────
# Page header
# ─────────────────────────────────────────────────────────────
st.title("Drug Candidate Explorer")
st.markdown(
    "Browse, filter, and compare FDA-approved drug candidates screened "
    "against neglected tropical disease protein targets."
)

# ─────────────────────────────────────────────────────────────
# Sidebar filters
# ─────────────────────────────────────────────────────────────
st.sidebar.header("Filters")
target_id = render_target_filter()
target_info = TARGET_PROTEINS[target_id]

# Load data for the selected target
df = get_drugs_for_target(target_id)

if df.empty:
    st.warning("No data found. Please run the mock data generator first.")
    st.code("python scripts/generate_mock_data.py")
    st.stop()

# Score range filter (based on actual data range)
score_min = float(df["consensus_score"].min())
score_max = float(df["consensus_score"].max())
min_score, max_score = render_score_filter(
    min_default=round(score_min, 2),
    max_default=round(score_max, 2),
)

# ADMET filters
admet_only, lipinski_only = render_admet_filter()

# Sort selector
sort_col = render_sort_selector()

# ─────────────────────────────────────────────────────────────
# Apply filters
# ─────────────────────────────────────────────────────────────
filtered = df[
    (df["consensus_score"] >= min_score)
    & (df["consensus_score"] <= max_score)
].copy()

if admet_only:
    filtered = filtered[filtered["overall_pass"] == 1]
if lipinski_only:
    filtered = filtered[filtered["lipinski_pass"] == 1]

# Sort
ascending = sort_col in ("consensus_rank", "vina_score", "ml_binding_score")
filtered = filtered.sort_values(sort_col, ascending=ascending).reset_index(drop=True)

# ─────────────────────────────────────────────────────────────
# Summary metrics
# ─────────────────────────────────────────────────────────────
st.subheader(f"Target: {target_info['name']}  ·  {target_info['disease']}")

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total Screened", len(df))
with col2:
    hits = len(df[df["consensus_score"] >= 0.6])
    st.metric("Hits (score ≥ 0.6)", hits)
with col3:
    safe_hits = len(df[(df["consensus_score"] >= 0.6) & (df["overall_pass"] == 1)])
    st.metric("ADMET-Safe Hits", safe_hits)
with col4:
    st.metric("Showing", len(filtered))

st.divider()

# ─────────────────────────────────────────────────────────────
# Charts row: distribution + top candidates
# ─────────────────────────────────────────────────────────────
chart_col1, chart_col2 = st.columns(2)
with chart_col1:
    st.plotly_chart(
        score_distribution_histogram(target_id),
        use_container_width=True,
    )
with chart_col2:
    st.plotly_chart(
        top_candidates_bar(target_id, n=10),
        use_container_width=True,
    )

st.divider()

# ─────────────────────────────────────────────────────────────
# Data table
# ─────────────────────────────────────────────────────────────
st.subheader("Drug Candidates")

# Prepare display dataframe
display_df = filtered[[
    "name", "drugbank_id", "original_indication",
    "vina_score", "ml_binding_score", "consensus_score", "consensus_rank",
    "overall_pass", "lipinski_pass", "lit_count",
]].copy()

display_df.columns = [
    "Drug Name", "DrugBank ID", "Indication",
    "Vina Score", "ML Score", "Consensus Score", "Rank",
    "ADMET Pass", "Lipinski Pass", "References",
]

# Convert boolean columns to readable labels
display_df["ADMET Pass"] = display_df["ADMET Pass"].map({1: "Pass", 0: "Fail"})
display_df["Lipinski Pass"] = display_df["Lipinski Pass"].map({1: "Pass", 0: "Fail"})

st.dataframe(
    display_df,
    use_container_width=True,
    height=400,
    column_config={
        "Vina Score": st.column_config.NumberColumn(format="%.2f"),
        "ML Score": st.column_config.NumberColumn(format="%.2f"),
        "Consensus Score": st.column_config.NumberColumn(format="%.4f"),
        "Rank": st.column_config.NumberColumn(format="%d"),
        "ADMET Pass": st.column_config.TextColumn(),
        "Lipinski Pass": st.column_config.TextColumn(),
        "References": st.column_config.NumberColumn(format="%d"),
    },
)

# ─────────────────────────────────────────────────────────────
# Drug detail panel
# ─────────────────────────────────────────────────────────────
st.divider()
st.subheader("Drug Detail Panel")

if filtered.empty:
    st.info("No drugs match your current filters. Try adjusting the filters.")
    st.stop()

# Style the drug selector to be more prominent
st.markdown("""<style>
div[data-testid="stSelectbox"] > div > div {
    border: 2px solid #1B4F72;
    border-radius: 8px;
    box-shadow: 0 2px 8px rgba(27, 79, 114, 0.15);
    padding: 2px;
}
div[data-testid="stSelectbox"] > div > div:hover {
    border-color: #2E86C1;
    box-shadow: 0 4px 12px rgba(46, 134, 193, 0.25);
}
</style>""", unsafe_allow_html=True)

# Drug selector
drug_options = filtered["drug_id"].tolist()
drug_names = filtered["name"].tolist()
name_map = dict(zip(drug_options, drug_names))

selected_drug_id = st.selectbox(
    "Select a drug to view details",
    options=drug_options,
    format_func=lambda x: f"{name_map[x]} ({x})",
)

if selected_drug_id:
    details = get_drug_details(selected_drug_id)
    if details is None:
        st.error("Drug details not found.")
        st.stop()

    # --- Properties ---
    st.markdown(f"### {details['name'].capitalize()}")

    prop_col1, prop_col2, prop_col3 = st.columns(3)
    with prop_col1:
        st.markdown(f"**DrugBank ID:** {details['drugbank_id']}")
        st.markdown(f"**Indication:** {details['original_indication']}")
    with prop_col2:
        st.markdown(f"**Molecular Weight:** {details['molecular_weight']:.1f} Da")
        st.markdown(f"**LogP:** {details['logp']:.2f}")
    with prop_col3:
        st.markdown(f"**SMILES:**")
        st.code(details["smiles"], language=None)

    st.divider()

    # --- Charts ---
    detail_chart1, detail_chart2 = st.columns(2)
    with detail_chart1:
        st.plotly_chart(
            score_comparison_bar(selected_drug_id),
            use_container_width=True,
        )
    with detail_chart2:
        st.plotly_chart(
            admet_radar(selected_drug_id),
            use_container_width=True,
        )

    # --- Literature ---
    lit_df = get_drug_literature(selected_drug_id, target_id)
    if not lit_df.empty:
        st.markdown("#### Literature Evidence")
        for _, row in lit_df.iterrows():
            st.markdown(
                f"- **{row['title']}**  \n"
                f"  PMID: [{row['pmid']}](https://pubmed.ncbi.nlm.nih.gov/{row['pmid']}/)  ·  "
                f"Relationship: {row['relationship']}  ·  "
                f"Confidence: {row['confidence']:.2f}"
            )
    else:
        st.caption("No literature evidence found for this drug-target combination.")
