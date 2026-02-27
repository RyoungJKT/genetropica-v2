"""Map conservation scores to 3D structure for visualization.

Writes conservation grades into the B-factor column of a PDB file,
generates a PyMOL script for offline rendering, and provides a
py3Dmol-based HTML viewer for the Streamlit dashboard.
"""

import logging
from pathlib import Path
from typing import Optional

import requests as http_requests
import streamlit.components.v1 as components

from src.utils.config import BASE_DIR

logger = logging.getLogger(__name__)

CONSURF_DIR: Path = BASE_DIR / "data" / "conservation" / "consurf"
RCSB_URL = "https://files.rcsb.org/download/{pdb_id}.pdb"


def fetch_pdb(pdb_id: str, timeout: int = 15) -> Optional[str]:
    """Fetch PDB file from RCSB.

    Args:
        pdb_id: 4-character PDB identifier.
        timeout: HTTP timeout in seconds.

    Returns:
        PDB file content as string, or None on failure.
    """
    try:
        resp = http_requests.get(
            RCSB_URL.format(pdb_id=pdb_id.upper()), timeout=timeout
        )
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        logger.warning("Failed to fetch PDB %s: %s", pdb_id, e)
        return None


def write_conservation_pdb(
    pdb_text: str,
    conservation_grades: dict[int, int],
    output_path: Path,
) -> Path:
    """Write a PDB file with conservation grades in the B-factor column.

    Replaces the B-factor field (columns 61-66) with the conservation
    grade scaled by 10 (range 10-90 for grades 1-9).

    Args:
        pdb_text: Original PDB file content.
        conservation_grades: Dict mapping residue number to grade (1-9).
        output_path: Path for the output PDB file.

    Returns:
        Path to the written file.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []

    for line in pdb_text.splitlines():
        if line.startswith(("ATOM", "HETATM")) and len(line) >= 66:
            try:
                resi = int(line[22:26].strip())
                grade = conservation_grades.get(resi, 5)
                bfactor = f"{grade * 10.0:6.2f}"
                line = line[:60] + bfactor + line[66:]
            except (ValueError, IndexError):
                pass
        lines.append(line)

    output_path.write_text("\n".join(lines))
    logger.info("Conservation PDB written: %s", output_path)
    return output_path


def generate_pymol_script(
    pdb_path: str = "5ZQK_conservation.pdb",
    binding_residues: Optional[list[int]] = None,
    output_path: Optional[Path] = None,
) -> str:
    """Generate a PyMOL .pml script for conservation visualization.

    Args:
        pdb_path: Path to the conservation-colored PDB file.
        binding_residues: Key binding site residues to highlight.
        output_path: Optional path to save the script.

    Returns:
        PyMOL script as string.
    """
    if binding_residues is None:
        binding_residues = [533, 663, 664, 737, 794]

    resi_selection = "+".join(str(r) for r in binding_residues)

    script = f"""# GeneTropica Conservation Visualization
# Load and color structure by conservation score (B-factor)

load {pdb_path}, protein
bg_color white

# Color by conservation (B-factor): blue = conserved, red = variable
spectrum b, blue_white_red, protein, minimum=10, maximum=90

# Show binding site residues as sticks
select binding_site, resi {resi_selection}
show sticks, binding_site
color yellow, binding_site and name CA

# Label key residues
label binding_site and name CA, "  %s%s" % (resn, resi)
set label_size, 14
set label_color, black

# Set view
orient
zoom protein, 5

# Ray trace for publication quality
set ray_opaque_background, on
ray 2400, 2400
png conservation_map.png, dpi=300
"""

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(script)
        logger.info("PyMOL script saved: %s", output_path)

    return script


def generate_conservation_viewer_html(
    pdb_id: str,
    conservation_grades: dict[int, int],
    binding_residues: Optional[list[int]] = None,
    width: int = 800,
    height: int = 600,
) -> str:
    """Generate py3Dmol HTML for conservation-colored 3D visualization.

    Colors residues on a blue (conserved, grade 9) to red (variable,
    grade 1) spectrum. Binding site residues shown as sticks with labels.

    Args:
        pdb_id: PDB identifier to fetch.
        conservation_grades: Dict mapping residue number to ConSurf grade 1-9.
        binding_residues: Residues to highlight as sticks.
        width: Viewer width in pixels.
        height: Viewer height in pixels.

    Returns:
        HTML string for embedding in Streamlit.
    """
    if binding_residues is None:
        binding_residues = [533, 663, 664, 737, 794]

    # Build JS color commands
    # Grade 9 (conserved) = blue (#0000FF)
    # Grade 5 (neutral) = white (#FFFFFF)
    # Grade 1 (variable) = red (#FF0000)
    color_commands: list[str] = []
    for resi, grade in conservation_grades.items():
        if grade >= 5:
            t = (grade - 5) / 4.0
            r = int(255 * (1 - t))
            g = int(255 * (1 - t))
            b = 255
        else:
            t = (grade - 1) / 4.0
            r = 255
            g = int(255 * t)
            b = int(255 * t)
        hex_color = f"0x{r:02x}{g:02x}{b:02x}"
        color_commands.append(
            f'viewer.setStyle({{resi: {resi}, chain: "A"}}, '
            f'{{cartoon: {{color: "{hex_color}"}}}});'
        )

    resi_list = ",".join(str(r) for r in binding_residues)
    binding_js = f"""
    viewer.setStyle({{resi: [{resi_list}], chain: "A"}},
        {{stick: {{radius: 0.15, color: "0xFFD700"}},
          cartoon: {{color: "0xFFD700"}}}});
    """

    label_js = "\n".join(
        f'viewer.addLabel("{r}", {{position: {{resi: {r}, chain: "A"}}, '
        f'backgroundColor: "0x333333", fontColor: "white", fontSize: 11}});'
        for r in binding_residues
    )

    color_js = "\n".join(color_commands)
    pdb_url = RCSB_URL.format(pdb_id=pdb_id.upper())

    html = f"""
    <script src="https://3Dmol.org/build/3Dmol-min.js"></script>
    <div id="conservation_viewer"
         style="width:100%;max-width:{width}px;height:{height}px;position:relative;">
    </div>
    <script>
        var viewer = $3Dmol.createViewer("conservation_viewer",
            {{backgroundColor: "white"}});
        jQuery.ajax("{pdb_url}", {{
            success: function(data) {{
                viewer.addModel(data, "pdb");
                viewer.setStyle({{}}, {{cartoon: {{color: "0xCCCCCC"}}}});
                {color_js}
                {binding_js}
                {label_js}
                viewer.zoomTo();
                viewer.render();
            }},
            error: function() {{
                document.getElementById("conservation_viewer").innerHTML =
                    "<p>Failed to load structure. Check network connection.</p>";
            }}
        }});
        window.addEventListener('resize', function() {{
            viewer.resize(); viewer.render();
        }});
    </script>
    <div style="text-align:center; margin-top:4px;">
        <span style="display:inline-block; margin-right:12px;">
            <span style="display:inline-block;width:12px;height:12px;background:#0000FF;
                         border-radius:2px;vertical-align:middle;margin-right:4px;"></span>
            <span style="font-size:0.8em;color:#555;">Conserved (9)</span>
        </span>
        <span style="display:inline-block; margin-right:12px;">
            <span style="display:inline-block;width:12px;height:12px;background:#FFFFFF;
                         border:1px solid #CCC;border-radius:2px;vertical-align:middle;
                         margin-right:4px;"></span>
            <span style="font-size:0.8em;color:#555;">Neutral (5)</span>
        </span>
        <span style="display:inline-block; margin-right:12px;">
            <span style="display:inline-block;width:12px;height:12px;background:#FF0000;
                         border-radius:2px;vertical-align:middle;margin-right:4px;"></span>
            <span style="font-size:0.8em;color:#555;">Variable (1)</span>
        </span>
        <span style="display:inline-block;">
            <span style="display:inline-block;width:12px;height:12px;background:#FFD700;
                         border-radius:2px;vertical-align:middle;margin-right:4px;"></span>
            <span style="font-size:0.8em;color:#555;">Binding Site</span>
        </span>
    </div>
    """
    return html


def render_conservation_viewer(
    pdb_id: str,
    conservation_grades: dict[int, int],
    binding_residues: Optional[list[int]] = None,
    width: int = 800,
    height: int = 600,
) -> None:
    """Render the conservation 3D viewer in Streamlit.

    Args:
        pdb_id: PDB identifier.
        conservation_grades: Dict mapping residue number to ConSurf grade.
        binding_residues: Residues to highlight.
        width: Viewer width.
        height: Viewer height.
    """
    html = generate_conservation_viewer_html(
        pdb_id, conservation_grades, binding_residues, width, height
    )
    components.html(html, height=height + 50)
