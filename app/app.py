"""GeneTropica — Main Streamlit app entry point."""

import streamlit as st

st.set_page_config(
    page_title="GeneTropica",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("GeneTropica")
st.subheader("Drug Repurposing for Neglected Tropical Diseases")
st.markdown(
    "Computational platform combining molecular docking with AI to identify "
    "existing drugs effective against dengue, chikungunya, and leptospirosis."
)
