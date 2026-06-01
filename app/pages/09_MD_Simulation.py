"""MD Simulation Analysis, 50 ns trajectory analysis for 3 drug candidates."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(page_title="MD Simulation", layout="wide")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.components.layout import render_sidebar
from app.components.charts import (
    MD_DRUG_COLORS,
    MD_DRUG_LABELS,
    md_bar_comparison,
    md_timeseries,
)

render_sidebar()

# ---------------------------------------------------------------------------
# Data directory
# ---------------------------------------------------------------------------
MD_DIR = PROJECT_ROOT / "data" / "md_simulation" / "comparison"
DRUGS = ["celecoxib", "methotrexate", "dasabuvir"]


# ---------------------------------------------------------------------------
# Data loading (cached)
# ---------------------------------------------------------------------------
@st.cache_data
def load_summary():
    path = MD_DIR / "comparison_summary.csv"
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


@st.cache_data
def load_per_drug_csv(prefix: str) -> dict:
    """Load per-drug CSVs matching a prefix (e.g. 'rmsd', 'rmsf')."""
    data = {}
    for drug in DRUGS:
        path = MD_DIR / f"{prefix}_{drug}.csv"
        if path.exists():
            data[drug] = pd.read_csv(path)
    return data


# ---------------------------------------------------------------------------
# Page header
# ---------------------------------------------------------------------------
st.title("Molecular Dynamics Simulation")
st.markdown(
    "**50 ns all-atom MD** of three drug candidates bound to "
    "**DENV NS5 RdRp** (PDB 5CCV, Chain A). "
    "Force field: AMBER99SB-ILDN + GAFF2, TIP3P water, 300 K, 1 bar."
)

# Check data availability
summary = load_summary()
if summary.empty:
    st.warning(
        "No MD analysis results found. Place CSV files from Colab "
        "analysis in `data/md_simulation/comparison/`."
    )
    st.stop()

# ===================================================================
# Section 1: Summary Overview
# ===================================================================
st.header("1. Summary Overview")

cols = st.columns(3)
for idx, drug in enumerate(DRUGS):
    row = summary[summary["Drug"] == drug.capitalize()]
    if row.empty:
        continue
    r = row.iloc[0]
    with cols[idx]:
        color = MD_DRUG_COLORS[drug]
        label = MD_DRUG_LABELS[drug]
        st.markdown(
            f"<h3 style='color:{color}; margin-bottom:0'>{label}</h3>",
            unsafe_allow_html=True,
        )
        c1, c2 = st.columns(2)
        c1.metric("Ligand RMSD", f"{float(r['Lig_RMSD_avg']):.2f} \u00c5")
        c2.metric("Protein RMSD", f"{float(r['Prot_RMSD_avg']):.2f} \u00c5")
        c3, c4 = st.columns(2)
        c3.metric("Avg H-bonds", f"{float(r['HBonds_avg']):.1f}")
        c4.metric("Min Distance", f"{float(r['MinDist_avg']):.2f} \u00c5")
        c5, c6 = st.columns(2)
        c5.metric("Contact Res (>50%)", str(r["ContactRes_gt50pct"]))
        c6.metric("Avg Contacts", str(r["Contacts_avg"]))

# Highlight best binder
best_drug = summary.loc[summary["MinDist_avg"].astype(float).idxmin(), "Drug"]
st.success(
    f"**{best_drug}** shows the strongest binding, lowest minimum distance "
    f"to the protein, indicating the most stable ligand-protein complex."
)

st.divider()

# ===================================================================
# Section 2: RMSD Analysis
# ===================================================================
st.header("2. RMSD Analysis")
st.markdown(
    "Root Mean Square Deviation measures structural drift from the starting "
    "conformation. Low, stable RMSD = equilibrated system."
)

rmsd_data = load_per_drug_csv("rmsd")
if rmsd_data:
    col1, col2 = st.columns(2)
    with col1:
        fig = md_timeseries(
            rmsd_data, "time_ns", "protein_rmsd_A",
            "Protein Backbone RMSD", "RMSD (\u00c5)",
        )
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        fig = md_timeseries(
            rmsd_data, "time_ns", "ligand_rmsd_A",
            "Ligand RMSD", "RMSD (\u00c5)",
        )
        st.plotly_chart(fig, use_container_width=True)
else:
    st.info("RMSD data not available.")

st.divider()

# ===================================================================
# Section 3: Structural Flexibility
# ===================================================================
st.header("3. Structural Flexibility")

rmsf_data = load_per_drug_csv("rmsf")
if rmsf_data:
    st.markdown(
        "**RMSF** (Root Mean Square Fluctuation) per residue, higher values "
        "indicate more flexible regions. Binding site residues should show "
        "moderate flexibility."
    )
    fig = md_timeseries(
        rmsf_data, "resid", "rmsf_A",
        "Per-Residue RMSF (C\u03b1 Atoms)", "RMSF (\u00c5)",
    )
    fig.update_layout(xaxis_title="Residue Number", height=450)
    st.plotly_chart(fig, use_container_width=True)

    # Rg note from summary
    rg_vals = summary["Rg_avg"].astype(float).tolist()
    drug_names = summary["Drug"].tolist()
    with st.expander("Radius of Gyration"):
        st.markdown(
            "Radius of gyration measures protein compactness. "
            "Stable Rg indicates no unfolding during simulation."
        )
        for name, rg in zip(drug_names, rg_vals):
            st.markdown(f"- **{name}**: Rg = {rg:.2f} \u00c5")
else:
    st.info("RMSF data not available.")

st.divider()

# ===================================================================
# Section 4: Binding Interactions
# ===================================================================
st.header("4. Binding Interactions")

hbond_data = load_per_drug_csv("hbonds")
contacts_data = load_per_drug_csv("contacts")

if hbond_data:
    col1, col2 = st.columns(2)
    with col1:
        fig = md_timeseries(
            hbond_data, "time_ns", "n_hbonds",
            "Drug-Protein H-bonds (smoothed)", "H-bonds",
            smooth_window=20,
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        labels = summary["Drug"].tolist()
        hb_avg = summary["HBonds_avg"].astype(float).tolist()
        hb_std = summary["HBonds_std"].astype(float).tolist()
        fig = md_bar_comparison(
            labels, hb_avg, hb_std,
            "Average H-bonds per Drug", "H-bonds",
        )
        st.plotly_chart(fig, use_container_width=True)

if contacts_data:
    st.subheader("Top Contact Residues")
    st.markdown(
        "Protein residues within 4.5 \u00c5 of the ligand. "
        "Higher occupancy = more persistent contact."
    )
    tabs = st.tabs([MD_DRUG_LABELS[d] for d in DRUGS if d in contacts_data])
    for tab, drug in zip(tabs, [d for d in DRUGS if d in contacts_data]):
        with tab:
            df = contacts_data[drug].head(15)
            if not df.empty:
                fig = md_bar_comparison(
                    [str(int(r)) for r in df["resid"]],
                    df["occupancy_pct"].tolist(),
                    None,
                    f"Top Contact Residues, {drug.capitalize()}",
                    "Occupancy (%)",
                )
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)

st.divider()

# ===================================================================
# Section 5: Binding Stability
# ===================================================================
st.header("5. Binding Stability")
st.markdown(
    "Minimum ligand-protein distance and atom-atom contact count "
    "over time, proxies for binding affinity."
)

proxy_data = load_per_drug_csv("binding_proxy")
if proxy_data:
    col1, col2 = st.columns(2)
    with col1:
        fig = md_timeseries(
            proxy_data, "time_ns", "min_dist_A",
            "Ligand-Protein Minimum Distance", "Distance (\u00c5)",
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig = md_timeseries(
            proxy_data, "time_ns", "n_contacts",
            "Atom-Atom Contacts (<4.5 \u00c5)", "Contacts",
        )
        st.plotly_chart(fig, use_container_width=True)

    # Bar comparisons
    col3, col4 = st.columns(2)
    with col3:
        labels = summary["Drug"].tolist()
        vals = summary["MinDist_avg"].astype(float).tolist()
        fig = md_bar_comparison(
            labels, vals, None,
            "Average Min Distance", "Distance (\u00c5)",
        )
        st.plotly_chart(fig, use_container_width=True)

    with col4:
        vals = summary["Contacts_avg"].astype(float).tolist()
        fig = md_bar_comparison(
            labels, vals, None,
            "Average Atom-Atom Contacts", "Contacts",
        )
        st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Binding proxy data not available.")

st.divider()

# ===================================================================
# Footer
# ===================================================================
st.caption(
    "MD simulations performed with GROMACS 2024.4 on Google Colab (NVIDIA H100). "
    "Analysis via MDAnalysis 2.x. "
    "GeneTropica, Russell Young, British School Jakarta."
)
