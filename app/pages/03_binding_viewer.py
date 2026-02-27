"""Binding Visualization dashboard page.

Interactive 3D viewer for protein-drug binding with multiple display
styles, binding pocket highlighting, and side-by-side comparison.
"""

import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.components.mol_viewer import render_binding_complex, render_comparison
from src.utils.config import DISEASES, TARGET_PROTEINS
from src.utils.db import (
    get_drug_details,
    get_drug_scores,
    get_drugs_for_target,
    get_interactions,
)

st.title("Binding Visualization")
st.markdown(
    "Explore 3D protein structures with highlighted binding pockets and "
    "compare how different drug candidates interact with disease targets."
)

# ─────────────────────────────────────────────────────────────
# Sidebar controls
# ─────────────────────────────────────────────────────────────
st.sidebar.header("Visualization Controls")

# Target selector
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
pdb_id = target_info["pdb_id"]

# Load top candidates for this target
df = get_drugs_for_target(target_id)
if df.empty:
    st.warning("No data found. Please run the mock data generator first.")
    st.code("python scripts/generate_mock_data.py")
    st.stop()

# Drug selector (top 20 candidates by default)
top_drugs = df.head(20)
drug_options = top_drugs["drug_id"].tolist()
drug_names = dict(zip(top_drugs["drug_id"], top_drugs["name"]))

selected_drug = st.sidebar.selectbox(
    "Drug Candidate",
    options=drug_options,
    format_func=lambda x: f"{drug_names[x].capitalize()} (rank #{top_drugs[top_drugs['drug_id']==x]['consensus_rank'].values[0]})",
)

st.sidebar.divider()

# Visualization style
vis_style = st.sidebar.selectbox(
    "Display Style",
    options=["cartoon", "stick", "sphere", "line"],
    index=0,
)

# Color scheme
color_scheme = st.sidebar.selectbox(
    "Color Scheme",
    options=["chain", "element", "secondary structure", "spectrum"],
    index=0,
)

# Show options
st.sidebar.divider()
show_surface = st.sidebar.toggle("Show surface", value=False)
show_pocket = st.sidebar.toggle("Highlight binding pocket", value=True)
compare_mode = st.sidebar.toggle("Compare two drugs", value=False)

# ─────────────────────────────────────────────────────────────
# Get interaction data to determine binding pocket residues
# ─────────────────────────────────────────────────────────────
interactions_df = get_interactions(selected_drug, target_id, pose_rank=1)

# Extract unique binding pocket residue numbers
pocket_residues = None
pocket_chain = "A"
if show_pocket and not interactions_df.empty:
    pocket_residues = sorted(interactions_df["residue_number"].unique().tolist())
    chains = interactions_df["chain"].unique()
    if len(chains) > 0:
        pocket_chain = chains[0]

# ─────────────────────────────────────────────────────────────
# Main viewer
# ─────────────────────────────────────────────────────────────
drug_details = get_drug_details(selected_drug)
drug_name = drug_details["name"].capitalize() if drug_details else selected_drug

if compare_mode:
    st.subheader("Side-by-Side Comparison")

    # Second drug selector
    other_options = [d for d in drug_options if d != selected_drug]
    if not other_options:
        st.info("Only one drug available — cannot compare.")
    else:
        drug2 = st.selectbox(
            "Compare with",
            options=other_options,
            format_func=lambda x: f"{drug_names[x].capitalize()} (rank #{top_drugs[top_drugs['drug_id']==x]['consensus_rank'].values[0]})",
        )
        drug2_details = get_drug_details(drug2)
        drug2_name = drug2_details["name"].capitalize() if drug2_details else drug2

        # Get binding residues for drug 2
        interactions2 = get_interactions(drug2, target_id, pose_rank=1)
        residues2 = None
        if show_pocket and not interactions2.empty:
            residues2 = sorted(interactions2["residue_number"].unique().tolist())

        render_comparison(
            pdb_id=pdb_id,
            drug1_name=drug_name,
            drug2_name=drug2_name,
            residues1=pocket_residues,
            residues2=residues2,
            chain=pocket_chain,
            style=vis_style,
            color_scheme=color_scheme,
            width=380,
            height=420,
        )

        # Comparison scores
        st.divider()
        sc1, sc2 = st.columns(2)
        drug_row = df[df["drug_id"] == selected_drug].iloc[0]
        drug2_row = df[df["drug_id"] == drug2].iloc[0]

        with sc1:
            st.metric("Vina Score", f"{drug_row['vina_score']:.2f} kcal/mol")
            st.metric("ML Score", f"{drug_row['ml_binding_score']:.2f}")
            st.metric("Consensus Rank", f"#{int(drug_row['consensus_rank'])}")
        with sc2:
            st.metric("Vina Score", f"{drug2_row['vina_score']:.2f} kcal/mol")
            st.metric("ML Score", f"{drug2_row['ml_binding_score']:.2f}")
            st.metric("Consensus Rank", f"#{int(drug2_row['consensus_rank'])}")

else:
    st.subheader(f"{drug_name} — {target_info['name']}")

    with st.spinner(f"Loading {pdb_id}..."):
        render_binding_complex(
            pdb_id=pdb_id,
            drug_name=drug_name,
            style=vis_style,
            color_scheme=color_scheme,
            highlight_residues=pocket_residues,
            highlight_chain=pocket_chain,
            show_surface=show_surface,
            width=800,
            height=550,
        )

# ─────────────────────────────────────────────────────────────
# Info panel — binding details
# ─────────────────────────────────────────────────────────────
st.divider()
st.subheader("Binding Details")

info_col1, info_col2 = st.columns(2)

# Scores
with info_col1:
    st.markdown("#### Binding Affinity")
    drug_row = df[df["drug_id"] == selected_drug]
    if not drug_row.empty:
        row = drug_row.iloc[0]
        m1, m2, m3 = st.columns(3)
        with m1:
            st.metric("Vina Score", f"{row['vina_score']:.2f}", help="kcal/mol (more negative = stronger)")
        with m2:
            st.metric("ML Score", f"{row['ml_binding_score']:.2f}", help="DeepChem predicted affinity")
        with m3:
            st.metric("Rank", f"#{int(row['consensus_rank'])}", help="Consensus rank for this target")

# Drug properties
with info_col2:
    st.markdown("#### Drug Properties")
    if drug_details:
        st.markdown(f"**Indication:** {drug_details['original_indication']}")
        st.markdown(f"**MW:** {drug_details['molecular_weight']:.1f} Da  |  **LogP:** {drug_details['logp']:.2f}")
        st.code(drug_details["smiles"], language=None)

# ─────────────────────────────────────────────────────────────
# Interaction details table
# ─────────────────────────────────────────────────────────────
st.divider()
st.subheader("Residue Interactions")

if interactions_df.empty:
    st.info("No interaction data available for this drug-target pair.")
else:
    # Summary by interaction type
    type_counts = interactions_df["interaction_type"].value_counts()

    type_cols = st.columns(min(len(type_counts), 4))
    type_icons = {
        "hydrogen_bond": "🔵",
        "hydrophobic": "🟤",
        "pi_stacking": "🟣",
        "salt_bridge": "🔴",
        "water_bridge": "💧",
        "pi_cation": "⚡",
    }
    for i, (itype, count) in enumerate(type_counts.items()):
        with type_cols[i % len(type_cols)]:
            icon = type_icons.get(itype, "·")
            label = itype.replace("_", " ").title()
            st.metric(f"{icon} {label}", count)

    # Full interaction table
    display_int = interactions_df.copy()
    display_int.columns = [
        "Residue", "Number", "Chain", "Interaction Type", "Distance (A)"
    ]
    display_int["Interaction Type"] = display_int["Interaction Type"].str.replace("_", " ").str.title()

    st.dataframe(
        display_int,
        use_container_width=True,
        height=300,
        column_config={
            "Distance (A)": st.column_config.NumberColumn(format="%.2f"),
        },
    )

    # Binding pocket summary
    n_residues = interactions_df["residue_number"].nunique()
    avg_dist = interactions_df["distance"].mean()
    st.caption(
        f"**{len(interactions_df)}** interactions across **{n_residues}** unique residues  |  "
        f"Average interaction distance: **{avg_dist:.2f} A**"
    )
