"""Shared layout components for consistent sidebar branding across all pages."""

import streamlit as st


def render_sidebar():
    """Render the standard GeneTropica sidebar with logo, nav guide, and footer."""
    with st.sidebar:
        st.image(
            "https://img.icons8.com/color/96/dna-helix.png",
            width=60,
        )
        st.title("GeneTropica")
        st.caption("Drug Repurposing for Neglected Tropical Diseases")
        st.divider()
        st.markdown(
            "**Navigate** using the pages in the sidebar to explore disease targets, "
            "drug candidates, binding interactions, AI insights, methods, "
            "validation, conservation analysis, ADMET profiling, and MD simulation."
        )
        st.divider()
        st.markdown(
            "Built by [Russell Young](https://github.com/RyoungJKT)  \n"
            "British School Jakarta"
        )
