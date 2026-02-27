"""Py3Dmol wrapper for 3D molecular visualization in Streamlit."""

import logging
from typing import Optional

import requests
import streamlit as st
import streamlit.components.v1 as components

logger = logging.getLogger(__name__)

_RCSB_URL = "https://files.rcsb.org/download/{pdb_id}.pdb"


@st.cache_data(ttl=3600, show_spinner=False)
def _fetch_pdb(pdb_id: str) -> Optional[str]:
    """Fetch PDB file content from RCSB.

    Args:
        pdb_id: 4-character PDB identifier.

    Returns:
        PDB file content as string, or None on failure.
    """
    try:
        resp = requests.get(
            _RCSB_URL.format(pdb_id=pdb_id.upper()),
            timeout=10,
        )
        resp.raise_for_status()
        return resp.text
    except requests.RequestException as e:
        logger.warning("Failed to fetch PDB %s: %s", pdb_id, e)
        return None


def render_protein(
    pdb_id: str,
    width: int = 400,
    height: int = 350,
    style: str = "cartoon",
    color_scheme: str = "chain",
) -> None:
    """Render a protein 3D structure using 3Dmol.js embedded in Streamlit.

    Args:
        pdb_id: 4-character PDB identifier (e.g. '2VBC').
        width: Viewer width in pixels.
        height: Viewer height in pixels.
        style: Visualization style — 'cartoon', 'stick', 'sphere', 'line'.
        color_scheme: Coloring method — 'chain', 'spectrum', 'ssPyMOL'.
    """
    pdb_data = _fetch_pdb(pdb_id)

    if pdb_data is None:
        st.warning(f"Could not load structure for PDB: {pdb_id}")
        st.caption(
            f"[View on RCSB →](https://www.rcsb.org/structure/{pdb_id})"
        )
        return

    # Escape backticks and backslashes in PDB data for safe JS embedding
    safe_pdb = (
        pdb_data
        .replace("\\", "\\\\")
        .replace("`", "\\`")
        .replace("${", "\\${")
    )

    color_map = {
        "chain": "chain",
        "spectrum": "spectrum",
        "ssPyMOL": "ssPyMOL",
    }
    color = color_map.get(color_scheme, "chain")

    html = f"""
    <script src="https://3Dmol.org/build/3Dmol-min.js"></script>
    <div id="viewer_{pdb_id}"
         style="width:{width}px;height:{height}px;position:relative;">
    </div>
    <script>
        var viewer = $3Dmol.createViewer("viewer_{pdb_id}", {{
            backgroundColor: "white"
        }});
        viewer.addModel(`{safe_pdb}`, "pdb");
        viewer.setStyle({{}}, {{
            {style}: {{color: "{color}"}}
        }});
        viewer.zoomTo();
        viewer.render();
    </script>
    """
    components.html(html, width=width + 10, height=height + 10)
