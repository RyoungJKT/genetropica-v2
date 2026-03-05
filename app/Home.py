"""GeneTropica — Main Streamlit app entry point."""

import sys
from pathlib import Path

import streamlit as st

# Ensure project root is importable
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.utils.db import init_db
from app.components.layout import render_sidebar

st.set_page_config(
    page_title="GeneTropica",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Responsive CSS — only activates on screens < 768px (mobile)
st.markdown("""<style>
@media (max-width: 768px) {
    /* Stack Streamlit columns vertically on mobile */
    [data-testid="column"] {
        width: 100% !important;
        flex: 1 0 100% !important;
    }
    /* Prevent 3D viewer iframes from overflowing */
    iframe {
        max-width: 100% !important;
    }
    /* Give metric cards some breathing room */
    [data-testid="stMetric"] {
        padding: 0.3rem 0;
    }
}
</style>""", unsafe_allow_html=True)

# Initialize database on first run
if "db_initialized" not in st.session_state:
    init_db()
    st.session_state.db_initialized = True

# --- Sidebar ---
render_sidebar()

# --- Home Page ---
st.title("GeneTropica")
st.subheader("AI-Powered Drug Repurposing for Neglected Tropical Diseases")

st.markdown("""
Neglected tropical diseases (NTDs) affect over **1 billion people** worldwide, with
Indonesia bearing a disproportionate burden of dengue, chikungunya, and leptospirosis.
Despite this, drug development for NTDs is severely underfunded.

**GeneTropica** takes a different approach: instead of developing new molecules from
scratch, this platform screens thousands of **existing FDA-approved drugs** against
disease protein targets to find new therapeutic uses — a strategy called
**drug repurposing**.
""")

st.divider()

# Pipeline summary cards
col1, col2, col3 = st.columns(3)
with col1:
    st.markdown("#### 🎯 6 Protein Targets")
    st.markdown("Across 3 neglected tropical diseases prevalent in Indonesia")
with col2:
    st.markdown("#### 💊 50 Drug Candidates")
    st.markdown("FDA-approved drugs screened for repurposing potential")
with col3:
    st.markdown("#### 🔬 7-Stage Pipeline")
    st.markdown(
        "From molecular docking to AI scoring, conservation analysis, "
        "and ADMET profiling"
    )

st.divider()

st.info(
    "👈 Use the **sidebar** to navigate between pages: Disease Overview, "
    "Drug Explorer, Binding Viewer, AI Insights, Methods, "
    "Methodology Validation, Conservation, and ADMET Profiling.",
    icon="ℹ️",
)
