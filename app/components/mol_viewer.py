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
        style: Visualization style, 'cartoon', 'stick', 'sphere', 'line'.
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
    <div id="v_{uid}" style="width:100%;max-width:{width}px;height:{height}px;position:relative;"></div>
    <script>
        var viewer = $3Dmol.createViewer("v_{uid}", {{backgroundColor: "white"}});
        viewer.addModel(`{safe}`, "pdb");
        viewer.setStyle({{}}, {{{style}: {{color: "{color}"}}}});
        viewer.zoomTo();
        viewer.render();
        window.addEventListener('resize', function() {{ viewer.resize(); viewer.render(); }});
    </script>
    """
    components.html(html, height=height + 10)


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

    Shows the protein with binding site residues highlighted
    and an info label.

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
    # Protein backbone = blue/cool tones; binding pocket = red/warm tones
    resi_js = ""
    if highlight_residues:
        resi_list = ",".join(str(r) for r in highlight_residues)
        resi_js = f"""
        // Binding pocket residues, warm red/magenta to contrast with protein
        viewer.setStyle(
            {{resi: [{resi_list}], chain: "{highlight_chain}"}},
            {{stick: {{color: "0xE74C3C", radius: 0.18}},
              {style}: {{color: "0xE74C3C", opacity: 0.5}}}}
        );

        // Add translucent surface around binding pocket only
        viewer.addSurface($3Dmol.SurfaceType.VDW, {{
            opacity: 0.25,
            color: "0xE74C3C"
        }}, {{resi: [{resi_list}], chain: "{highlight_chain}"}});
        """

    surface_js = ""
    if show_surface:
        surface_js = """
        // Whole-protein surface
        viewer.addSurface($3Dmol.SurfaceType.VDW, {
            opacity: 0.12, color: "0x85C1E9"
        });
        """

    # Force protein backbone to a cool blue/teal when pocket is highlighted
    # so the red binding pocket stands out clearly
    if highlight_residues:
        protein_color = "0x2E86C1"
    else:
        protein_color = f'"{color}"'

    html = f"""
    <script src="https://3Dmol.org/build/3Dmol-min.js"></script>
    <div id="v_{uid}" style="width:100%;max-width:{width}px;height:{height}px;position:relative;">
    </div>
    <script>
        var viewer = $3Dmol.createViewer("v_{uid}", {{backgroundColor: "white"}});
        viewer.addModel(`{safe}`, "pdb");

        // Protein backbone, cool blue
        viewer.setStyle({{}}, {{{style}: {{color: {protein_color}}}}});

        {resi_js}
        {surface_js}

        viewer.zoomTo();
        viewer.render();
        window.addEventListener('resize', function() {{ viewer.resize(); viewer.render(); }});
    </script>
    <div style="text-align:center; margin-top:4px; flex-wrap:wrap;">
        <span style="display:inline-block; margin-right:16px; margin-bottom:4px;">
            <span style="display:inline-block;width:12px;height:12px;background:#2E86C1;
                         border-radius:2px;vertical-align:middle;margin-right:4px;"></span>
            <span style="font-size:0.8em;color:#555;">Protein</span>
        </span>
        <span style="display:inline-block; margin-right:16px; margin-bottom:4px;">
            <span style="display:inline-block;width:12px;height:12px;background:#E74C3C;
                         border-radius:2px;vertical-align:middle;margin-right:4px;"></span>
            <span style="font-size:0.8em;color:#555;">Binding Pocket ({drug_name})</span>
        </span>
        <span style="display:inline-block; background:#FFF3CD; padding:2px 8px; border-radius:4px;
                     font-size:0.75em; color:#856404; margin-bottom:4px;">
            Preview, docked poses will replace this view
        </span>
    </div>
    """
    components.html(html, height=height + 70)


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
