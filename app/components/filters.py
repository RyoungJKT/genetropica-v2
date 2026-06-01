"""Sidebar filter components for the dashboard."""

import streamlit as st

from src.utils.config import DISEASES, TARGET_PROTEINS


def render_target_filter() -> str:
    """Render a disease/target selector in the sidebar.

    Returns:
        Selected target_id string.
    """
    options: list[str] = []
    labels: dict[str, str] = {}
    for disease, info in DISEASES.items():
        for tid in info["targets"]:
            target = TARGET_PROTEINS[tid]
            options.append(tid)
            labels[tid] = f"{disease} — {target['name']}"

    selected = st.sidebar.selectbox(
        "Protein Target",
        options=options,
        format_func=lambda x: labels[x],
        help="Select a disease protein target to explore drug candidates against.",
    )
    return selected


def render_score_filter(
    min_default: float = 0.0,
    max_default: float = 1.0,
) -> tuple[float, float]:
    """Render a consensus score range slider in the sidebar.

    Returns:
        Tuple of (min_score, max_score).
    """
    score_range = st.sidebar.slider(
        "Score Range",
        min_value=min_default,
        max_value=max_default,
        value=(min_default, max_default),
        step=0.01,
        help="Filter drugs by score.",
    )
    return score_range


def render_admet_filter() -> tuple[bool, bool]:
    """Render ADMET and Lipinski filter toggles in the sidebar.

    Returns:
        Tuple of (admet_only, lipinski_only) booleans.
    """
    admet_only = st.sidebar.toggle(
        "ADMET-safe only",
        value=False,
        help="Show only drugs that pass all ADMET safety criteria.",
    )
    lipinski_only = st.sidebar.toggle(
        "Lipinski-compliant only",
        value=False,
        help="Show only drugs that satisfy Lipinski's Rule of Five.",
    )
    return admet_only, lipinski_only


def render_sort_selector() -> str:
    """Render a sort-by selector in the sidebar.

    Returns:
        Column name to sort by.
    """
    sort_options = {
        "vina_rank": "Vina rank (best first)",
        "le_rank": "Ligand-efficiency rank (best first)",
        "ligand_efficiency": "Ligand efficiency (highest first)",
        "vina_score": "Vina score (best first)",
    }
    selected = st.sidebar.selectbox(
        "Sort by",
        options=list(sort_options.keys()),
        format_func=lambda x: sort_options[x],
    )
    return selected


def render_druglike_filter() -> bool:
    """Render a drug-like (MW 250-600 Da) toggle in the sidebar.

    Returns:
        True if only drug-like candidates should be shown.
    """
    return st.sidebar.toggle(
        "Drug-like only (MW 250-600)",
        value=True,
        help="Restrict to a drug-like molecular-weight window. This removes both "
             "the oversized molecules that dominate raw Vina (size bias) and the "
             "tiny fragments that dominate ligand efficiency.",
    )
