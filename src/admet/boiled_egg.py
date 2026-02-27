"""BOILED-Egg classification for GI absorption and BBB permeation.

Predicts passive gastrointestinal (GI) absorption and blood-brain barrier
(BBB) permeation using the BOILED-Egg model based on TPSA and WLogP.

Reference:
    Daina & Zoete, ChemMedChem 2016, 11, 1117-1121.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# BOILED-Egg boundary constants
# ---------------------------------------------------------------------------

GI_TPSA_MAX: float = 142.0
GI_LOGP_MIN: float = -2.3
GI_LOGP_MAX: float = 6.8

BBB_TPSA_MAX: float = 79.0
BBB_LOGP_MIN: float = -0.5
BBB_LOGP_MAX: float = 5.0


# ---------------------------------------------------------------------------
# Classification functions
# ---------------------------------------------------------------------------

def classify_absorption(tpsa: float, wlogp: float) -> str:
    """Classify passive GI absorption as 'High' or 'Low'.

    A compound is predicted to have high GI absorption if its TPSA is at most
    142.0 A^2 and its WLogP falls between -2.3 and 6.8 (inclusive).

    Args:
        tpsa: Topological polar surface area.
        wlogp: Wildman-Crippen LogP.

    Returns:
        'High' if within the white region of the BOILED-Egg, else 'Low'.
    """
    if tpsa <= GI_TPSA_MAX and GI_LOGP_MIN <= wlogp <= GI_LOGP_MAX:
        return "High"
    return "Low"


def classify_bbb(tpsa: float, wlogp: float) -> str:
    """Classify blood-brain barrier permeation as 'Yes' or 'No'.

    A compound is predicted to permeate the BBB if its TPSA is at most
    79.0 A^2 and its WLogP falls between -0.5 and 5.0 (inclusive).

    Args:
        tpsa: Topological polar surface area.
        wlogp: Wildman-Crippen LogP.

    Returns:
        'Yes' if within the yolk region of the BOILED-Egg, else 'No'.
    """
    if tpsa <= BBB_TPSA_MAX and BBB_LOGP_MIN <= wlogp <= BBB_LOGP_MAX:
        return "Yes"
    return "No"
