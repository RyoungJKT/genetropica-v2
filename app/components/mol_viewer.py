"""Py3Dmol wrapper for 3D molecular visualization in Streamlit."""

import hashlib
import logging
from typing import Optional

import requests
import streamlit as st
import streamlit.components.v1 as components

logger = logging.getLogger(__name__)

_RCSB_URL = "https://files.rcsb.org/download/{pdb_id}.pdb"

# Color scheme mappings for 3Dmol.js
_COLOR_SCHEMES = {
    "chain": "chain",
    "element": "default",
    "secondary structure": "ssPyMOL",
    "spectrum": "spectrum",
}


def _safe_pdb(pdb_data: str) -> str:
    """Escape PDB data for safe JS template literal embedding."""
    return (
        pdb_data
        .replace("\\", "\\\\")
        .replace("`", "\\`")
        .replace("${", "\\${")
    )


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
        color_scheme: Coloring method key from _COLOR_SCHEMES.
    """
    pdb_data = _fetch_pdb(pdb_id)

    if pdb_data is None:
        st.warning(f"Could not load structure for PDB: {pdb_id}")
        st.caption(
            f"[View on RCSB →](https://www.rcsb.org/structure/{pdb_id})"
        )
        return

    safe = _safe_pdb(pdb_data)
    color = _COLOR_SCHEMES.get(color_scheme, "chain")
    uid = hashlib.md5(f"{pdb_id}_{style}_{color}".encode()).hexdigest()[:8]

    html = f"""
    <script src="https://3Dmol.org/build/3Dmol-min.js"></script>
    <div id="v_{uid}" style="width:{width}px;height:{height}px;position:relative;"></div>
    <script>
        var viewer = $3Dmol.createViewer("v_{uid}", {{backgroundColor: "white"}});
        viewer.addModel(`{safe}`, "pdb");
        viewer.setStyle({{}}, {{{style}: {{color: "{color}"}}}});
        viewer.zoomTo();
        viewer.render();
    </script>
    """
    components.html(html, width=width + 10, height=height + 10)


def render_binding_complex(
    pdb_id: str,
    drug_name: str,
    style: str = "cartoon",
    color_scheme: str = "chain",
    highlight_residues: Optional[list[int]] = None,
    highlight_chain: str = "A",
    show_surface: bool = False,
    width: int = 800,
    height: int = 600,
) -> None:
    """Render protein with highlighted binding pocket and annotation.

    In mock mode (no actual docked poses), shows the protein with
    binding site residues highlighted and an info label.

    Args:
        pdb_id: 4-character PDB identifier.
        drug_name: Name of the drug candidate (for annotation).
        style: Visualization style for the protein backbone.
        color_scheme: Color scheme for the protein.
        highlight_residues: List of residue numbers to highlight as binding pocket.
        highlight_chain: Chain ID for highlighted residues.
        show_surface: Whether to show a translucent surface.
        width: Viewer width in pixels.
        height: Viewer height in pixels.
    """
    pdb_data = _fetch_pdb(pdb_id)

    if pdb_data is None:
        st.warning(f"Could not load structure for PDB: {pdb_id}")
        st.caption(
            f"[View on RCSB →](https://www.rcsb.org/structure/{pdb_id})"
        )
        return

    safe = _safe_pdb(pdb_data)
    color = _COLOR_SCHEMES.get(color_scheme, "chain")
    uid = hashlib.md5(
        f"bind_{pdb_id}_{drug_name}_{style}_{show_surface}".encode()
    ).hexdigest()[:8]

    # Build residue selection JS for binding pocket highlight
    resi_js = ""
    if highlight_residues:
        resi_list = ",".join(str(r) for r in highlight_residues)
        resi_js = f"""
        // Highlight binding pocket residues
        viewer.setStyle(
            {{resi: [{resi_list}], chain: "{highlight_chain}"}},
            {{stick: {{colorscheme: "orangeCarbon", radius: 0.15}},
              {style}: {{color: "{color}", opacity: 0.7}}}}
        );
        """

    surface_js = ""
    if show_surface:
        surface_js = """
        viewer.addSurface($3Dmol.SurfaceType.VDW, {
            opacity: 0.15, color: "white"
        });
        """

    html = f"""
    <script src="https://3Dmol.org/build/3Dmol-min.js"></script>
    <div id="v_{uid}" style="width:{width}px;height:{height}px;position:relative;">
    </div>
    <script>
        var viewer = $3Dmol.createViewer("v_{uid}", {{backgroundColor: "white"}});
        viewer.addModel(`{safe}`, "pdb");

        // Base protein style
        viewer.setStyle({{}}, {{{style}: {{color: "{color}"}}}});

        {resi_js}
        {surface_js}

        viewer.zoomTo();
        viewer.render();
    </script>
    <div style="text-align:center; margin-top:4px;">
        <span style="background:#FFF3CD; padding:3px 10px; border-radius:4px;
                     font-size:0.8em; color:#856404;">
            Preview mode — actual docking poses will replace this view
        </span>
    </div>
    """
    components.html(html, width=width + 10, height=height + 60)


def render_comparison(
    pdb_id: str,
    drug1_name: str,
    drug2_name: str,
    residues1: Optional[list[int]] = None,
    residues2: Optional[list[int]] = None,
    chain: str = "A",
    style: str = "cartoon",
    color_scheme: str = "chain",
    width: int = 400,
    height: int = 450,
) -> None:
    """Render two side-by-side viewers for drug comparison.

    Args:
        pdb_id: PDB identifier (same target for both).
        drug1_name: First drug name.
        drug2_name: Second drug name.
        residues1: Binding residues for drug 1.
        residues2: Binding residues for drug 2.
        chain: Chain ID.
        style: Visualization style.
        color_scheme: Color scheme.
        width: Width of each viewer.
        height: Height of each viewer.
    """
    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f"**{drug1_name}**")
        render_binding_complex(
            pdb_id=pdb_id,
            drug_name=drug1_name,
            style=style,
            color_scheme=color_scheme,
            highlight_residues=residues1,
            highlight_chain=chain,
            width=width,
            height=height,
        )

    with col2:
        st.markdown(f"**{drug2_name}**")
        render_binding_complex(
            pdb_id=pdb_id,
            drug_name=drug2_name,
            style=style,
            color_scheme=color_scheme,
            highlight_residues=residues2,
            highlight_chain=chain,
            width=width,
            height=height,
        )
