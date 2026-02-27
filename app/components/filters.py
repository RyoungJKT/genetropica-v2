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
        "Consensus Score Range",
        min_value=min_default,
        max_value=max_default,
        value=(min_default, max_default),
        step=0.01,
        help="Filter drugs by consensus score (higher = stronger candidate).",
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
        "consensus_rank": "Consensus Rank",
        "vina_score": "Vina Score (best first)",
        "ml_binding_score": "ML Score (best first)",
        "consensus_score": "Consensus Score (highest first)",
    }
    selected = st.sidebar.selectbox(
        "Sort by",
        options=list(sort_options.keys()),
        format_func=lambda x: sort_options[x],
    )
    return selected
