"""Methods & Reproducibility dashboard page.

Pipeline diagram, data sources, computational methods,
results download, and reproducibility instructions.
"""

import sys
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st

st.set_page_config(layout="wide")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.components.layout import render_sidebar
from src.utils.config import DISEASES, TARGET_PROTEINS
from src.utils.db import (
    export_admet_csv,
    export_literature_csv,
    export_results_csv,
    export_top_candidates,
)

render_sidebar()

st.title("Methods & Reproducibility")
st.markdown(
    "Full documentation of the GeneTropica computational pipeline, "
    "data sources, parameters, and downloadable results."
)

# ─────────────────────────────────────────────────────────────
# Section 1, Pipeline Diagram
# ─────────────────────────────────────────────────────────────
st.header("1. Pipeline Overview")
st.markdown(
    "GeneTropica follows a five-stage hybrid pipeline combining physics-based "
    "molecular docking with machine-learning rescoring, safety profiling, "
    "and automated literature mining."
)

# Build pipeline flowchart using Plotly scatter + annotations
_stages = [
    ("Data Acquisition", "Gather FDA-approved drug\nstructures and protein\ntargets from public databases"),
    ("Structure Prediction", "Predict 3D protein structures\nusing ESMFold where crystal\nstructures are unavailable"),
    ("Molecular Docking", "Simulate drug-protein binding\nwith AutoDock Vina to estimate\nbinding affinity (kcal/mol)"),
    ("AI Scoring & Filtering", "ML rescoring (Random Forest),\nADMET safety profiling,\nPubMed NLP literature mining"),
    ("Interactive Dashboard", "Streamlit web app with 3D\nvisualization, ranked candidates,\nand supporting evidence"),
]

fig = go.Figure()

# Stage boxes
n = len(_stages)
y_positions = list(range(n, 0, -1))  # top to bottom

for i, (title, desc) in enumerate(_stages):
    y = y_positions[i]
    # Stage number circle
    fig.add_trace(go.Scatter(
        x=[0.5], y=[y],
        mode="markers+text",
        marker=dict(size=36, color="#1B4F72"),
        text=[str(i + 1)],
        textfont=dict(color="white", size=14),
        textposition="middle center",
        showlegend=False,
        hoverinfo="skip",
    ))
    # Title
    fig.add_annotation(
        x=1.2, y=y + 0.08,
        text=f"<b>{title}</b>",
        showarrow=False,
        font=dict(size=14, color="#1B4F72"),
        xanchor="left",
    )
    # Description
    fig.add_annotation(
        x=1.2, y=y - 0.22,
        text=desc.replace("\n", "<br>"),
        showarrow=False,
        font=dict(size=11, color="#555"),
        xanchor="left",
        align="left",
    )

# Arrows between stages
for i in range(n - 1):
    fig.add_annotation(
        x=0.5, y=y_positions[i] - 0.4,
        ax=0.5, ay=y_positions[i + 1] + 0.4,
        xref="x", yref="y", axref="x", ayref="y",
        showarrow=True,
        arrowhead=2, arrowsize=1.5, arrowwidth=2,
        arrowcolor="#2E86C1",
    )

fig.update_layout(
    xaxis=dict(visible=False, range=[-0.5, 6]),
    yaxis=dict(visible=False, range=[0.2, n + 0.8]),
    height=500,
    margin=dict(l=0, r=0, t=10, b=10),
    plot_bgcolor="white",
)

st.plotly_chart(fig, use_container_width=True)

# Expandable stage details
with st.expander("Stage 1, Data Acquisition"):
    st.markdown("""
**Input:** Drug names, disease protein identifiers

**Process:**
- Query DrugBank and ZINC15 for FDA-approved drug 3D structures (SDF/MOL2)
- Convert to PDBQT format using Open Babel for Vina compatibility
- Download protein structures from RCSB PDB (experimental X-ray/cryo-EM)
- Retrieve sequence and functional annotations from UniProt

**Output:** 50 drug PDBQT files, 6 protein PDB/PDBQT files
""")

with st.expander("Stage 2, Structure Prediction"):
    st.markdown("""
**Input:** Protein sequences without experimental structures

**Process:**
- Run ESMFold (Meta AI) for fast single-sequence structure prediction
- Fall back to ColabFold (AlphaFold2 + MMseqs2) for higher accuracy when needed
- Validate predicted structures against known binding site residues
- Prepare predicted structures for docking (add hydrogens, compute charges)

**Output:** Predicted 3D structures for any targets lacking PDB entries
""")

with st.expander("Stage 3, Molecular Docking"):
    st.markdown("""
**Input:** Drug PDBQT files + protein PDBQT files

**Process:**
- Define search box centered on known/predicted binding site
- Run AutoDock Vina v1.2.7 with exhaustiveness=8
- Generate top 3 poses per drug-target pair
- Extract binding energy scores (kcal/mol)

**Output:** 882 docking results (49 drugs x 6 targets x 3 poses)

**Key parameters:**
| Parameter | Value |
|-----------|-------|
| Exhaustiveness | 8 |
| Number of poses | 3 |
| Energy range | 3 kcal/mol |
| Search box | 25 x 25 x 25 A (centered on binding site) |
""")

with st.expander("Stage 4, AI Scoring & Filtering"):
    st.markdown("""
**Input:** Docking poses + drug SMILES + protein sequences

**Process:**
- **Random Forest ML rescoring**, Classifier on 2048-bit Morgan fingerprints
  + Vina score; a target-agnostic activity prior (supporting signal)
- **Dual-metric ranking**, Rank drug-like candidates (MW 250-600) by Vina
  score and ligand efficiency, shown side by side
- **ADMET prediction**, Evaluate Lipinski compliance, hepatotoxicity risk,
  hERG inhibition risk, oral bioavailability
- **PubMed search**, Search for existing drug-disease literature via
  NCBI E-utilities with keyword matching

**Output:** Ranked candidate list with safety profiles and literature evidence
""")

with st.expander("Stage 5, Interactive Dashboard"):
    st.markdown("""
**Input:** Complete results database

**Process:**
- Build multi-page Streamlit application
- Embed 3Dmol.js for interactive 3D protein visualization
- Create Plotly charts for scoring analysis
- Implement filtering, sorting, and comparison tools

**Output:** This web application
""")


# ─────────────────────────────────────────────────────────────
# Section 2, Data Sources
# ─────────────────────────────────────────────────────────────
st.divider()
st.header("2. Data Sources")

data_sources = {
    "Source": [
        "DrugBank",
        "ZINC15",
        "PubChem",
        "RCSB PDB",
        "UniProt",
        "AlphaFold DB",
        "PubMed",
    ],
    "URL": [
        "https://go.drugbank.com",
        "https://zinc15.docking.org",
        "https://pubchem.ncbi.nlm.nih.gov",
        "https://www.rcsb.org",
        "https://www.uniprot.org",
        "https://alphafold.ebi.ac.uk",
        "https://pubmed.ncbi.nlm.nih.gov",
    ],
    "Data Retrieved": [
        "FDA-approved drug structures, indications, SMILES",
        "3D conformers for docking (SDF format)",
        "Molecular properties, cross-references",
        "Experimental protein structures (PDB format)",
        "Protein sequences, functional annotations",
        "Predicted structures for targets without PDB entries",
        "Drug-disease literature for evidence mining",
    ],
    "Format": [
        "SDF, CSV",
        "SDF, MOL2",
        "JSON, SDF",
        "PDB, mmCIF",
        "FASTA, XML",
        "PDB, mmCIF",
        "XML (E-utilities API)",
    ],
}

st.dataframe(
    data_sources,
    use_container_width=True,
    column_config={
        "URL": st.column_config.LinkColumn(display_text="Link"),
    },
)


# ─────────────────────────────────────────────────────────────
# Section 3, Computational Methods
# ─────────────────────────────────────────────────────────────
st.divider()
st.header("3. Computational Methods")

method_col1, method_col2 = st.columns(2)

with method_col1:
    st.subheader("Molecular Docking")
    st.markdown("""
| Parameter | Value |
|-----------|-------|
| Software | AutoDock Vina 1.2.7 |
| Ligand preparation | Open Babel 3.1 + RDKit ETKDG |
| Search box | 25 x 25 x 25 A |
| Exhaustiveness | 8 |
| Num. poses | 3 per drug-target pair |
| Energy range | 3 kcal/mol |
| Scoring metric | Binding energy (kcal/mol) |
""")

    st.subheader("ADMET Prediction")
    st.markdown("""
| Property | Method | Threshold |
|----------|--------|-----------|
| Lipinski Rule of 5 | Descriptor check | All 4 rules |
| Hepatotoxicity | Random Forest | Risk < 0.5 |
| hERG inhibition | SVM classifier | Risk < 0.5 |
| Oral bioavailability | Regression | Score > 0.5 |
""")

with method_col2:
    st.subheader("ML Rescoring")
    st.markdown("""
| Parameter | Value |
|-----------|-------|
| Framework | scikit-learn |
| Architecture | Random Forest Classifier |
| Training data | 166 compounds from ChEMBL (HCV NS5B, Dengue NS5, Influenza RdRp) |
| Input features | 2048-bit Morgan fingerprints (radius=2) + normalised Vina score |
| Feature dimension | 2049 |
| ChEMBL CV AUC | 0.875 ± 0.094 (5-fold stratified) |
| Consensus weight | Target-specific (0.9 ML for NS5, 0.6 ML for others) |
| Validation ML AUC | 0.509 (NS5 RdRp inhibitors vs library) |
""")

    st.subheader("NLP Literature Mining")
    st.markdown("""
| Parameter | Value |
|-----------|-------|
| Method | Keyword and synonym matching |
| Search API | NCBI E-utilities (PubMed esearch + efetch) |
| Output | PubMed entries with PMIDs for traceability |
""")

st.subheader("Ranking")
st.markdown("""
Drug-like candidates (MW 250-600) are ranked by **AutoDock Vina score** and by
**ligand efficiency** (binding energy per heavy atom), shown side by side, to
control for docking's size bias. The RandomForest ML score is a target-agnostic
activity prior, used only as a supporting signal.

A legacy weighted consensus (below) is retained in the database for reference but
is **not** the headline ranking, because weighting the target-agnostic ML term
heavily made one molecule top nearly every target:
""")
st.latex(r"\text{Consensus (legacy)} = 0.4 \times \hat{V} + 0.6 \times \hat{M}")


# ─────────────────────────────────────────────────────────────
# Section 4, Results Download
# ─────────────────────────────────────────────────────────────
st.divider()
st.header("4. Download Results")
st.markdown("Export screening results as CSV files for further analysis.")

# Target selector for per-target exports
target_options = []
target_labels = {}
for disease, info in DISEASES.items():
    for tid in info["targets"]:
        target_options.append(tid)
        target_labels[tid] = f"{disease}, {TARGET_PROTEINS[tid]['name']}"

dl_target = st.selectbox(
    "Select target for per-target downloads",
    options=target_options,
    format_func=lambda x: target_labels[x],
    key="dl_target",
)

dl1, dl2, dl3, dl4 = st.columns(4)

with dl1:
    full_df = export_results_csv(dl_target)
    if not full_df.empty:
        st.download_button(
            label=f"Full Results ({len(full_df)} drugs)",
            data=full_df.to_csv(index=False),
            file_name=f"genetropica_{dl_target}_full_results.csv",
            mime="text/csv",
        )
    else:
        st.caption("No data available")

with dl2:
    top_df = export_top_candidates(dl_target, n=10)
    if not top_df.empty:
        st.download_button(
            label=f"Top 10 Candidates ({len(top_df)})",
            data=top_df.to_csv(index=False),
            file_name=f"genetropica_{dl_target}_top10.csv",
            mime="text/csv",
        )
    else:
        st.caption("No ADMET-safe candidates")

with dl3:
    admet_df = export_admet_csv()
    if not admet_df.empty:
        st.download_button(
            label=f"ADMET Profiles ({len(admet_df)})",
            data=admet_df.to_csv(index=False),
            file_name="genetropica_admet_profiles.csv",
            mime="text/csv",
        )
    else:
        st.caption("No ADMET data")

with dl4:
    lit_df = export_literature_csv()
    if not lit_df.empty:
        st.download_button(
            label=f"Literature ({len(lit_df)} refs)",
            data=lit_df.to_csv(index=False),
            file_name="genetropica_literature_evidence.csv",
            mime="text/csv",
        )
    else:
        st.caption("No literature data")


# ─────────────────────────────────────────────────────────────
# Section 5, Reproducibility
# ─────────────────────────────────────────────────────────────
st.divider()
st.header("5. Reproducibility")

st.subheader("Source Code")
st.markdown(
    "The full source code is available on GitHub:  \n"
    "[github.com/RyoungJKT/genetropica-v2]"
    "(https://github.com/RyoungJKT/genetropica-v2)"
)

st.subheader("Environment Setup")
st.code(
    """# Clone repository
git clone https://github.com/RyoungJKT/genetropica-v2.git
cd genetropica-v2

# Create conda environment
conda env create -f environment.yml
conda activate genetropica

# Generate database
python scripts/generate_mock_data.py

# Launch dashboard
streamlit run app/app.py""",
    language="bash",
)

st.subheader("Running the Full Pipeline")
st.markdown("""
To reproduce results from scratch:

1. **Data acquisition**, `python -m src.data_acquisition.fetch_drugs`
2. **Structure preparation**, `python -m src.structure_prediction.predict`
3. **Molecular docking**, `python -m src.docking.run_vina`
4. **AI scoring**, `python -m src.ai_scoring.rescore`
5. **Launch dashboard**, `streamlit run app/app.py`

Each stage writes to the SQLite database at `data/database/genetropica.db`.
""")

st.subheader("Citation")
st.code(
    """Russell Young (2026). GeneTropica: AI-Powered Drug Repurposing
for Neglected Tropical Diseases in Indonesia. British School Jakarta.
https://github.com/RyoungJKT/genetropica-v2""",
    language=None,
)

st.divider()
st.caption(
    "GeneTropica v2, Methods & Pipeline | Russell Young, British School Jakarta"
)
