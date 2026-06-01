"""Disease overview dashboard page.

Displays disease burden metrics, protein target cards with 3D viewers,
and a visual overview of the GeneTropica pipeline.
"""

import sys
from pathlib import Path

import streamlit as st

st.set_page_config(layout="wide")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.components.layout import render_sidebar
from app.components.mol_viewer import render_protein
from src.utils.config import DISEASES, TARGET_PROTEINS

render_sidebar()

st.title("Disease Overview")
st.markdown(
    "Understanding the neglected tropical diseases targeted by GeneTropica "
    "and the protein structures we use for drug screening."
)

# ─────────────────────────────────────────────────────────────
# Section 1, Disease Burden in Indonesia
# ─────────────────────────────────────────────────────────────
st.header("Disease Burden in Indonesia")

col_d, col_c, col_l = st.columns(3)

with col_d:
    st.metric(label="Dengue", value="~140,000", delta="cases/year (est.)")
    st.markdown("""
    Dengue is Indonesia's most widespread arboviral disease, transmitted by
    *Aedes aegypti* mosquitoes. All four serotypes circulate year-round, with
    periodic outbreaks causing thousands of hospitalizations.

    **Why repurposing matters:** No specific antiviral treatment exists. Current
    care is supportive only, fluids, monitoring, and pain management.
    """)

with col_c:
    st.metric(label="Chikungunya", value="Endemic", delta="periodic outbreaks")
    st.markdown("""
    Chikungunya causes debilitating joint pain that can persist for months.
    Indonesia has experienced multiple large outbreaks, particularly in
    Java and Sumatra, since the virus re-emerged in 2001.

    **Why repurposing matters:** There is no approved antiviral or vaccine
    widely available. Treatment is limited to symptom management.
    """)

with col_l:
    st.metric(label="Leptospirosis", value="~8,000", delta="cases/year (est.)")
    st.markdown("""
    Leptospirosis is a bacterial zoonosis spread through contact with
    contaminated water, especially during monsoon flooding. Indonesia
    reports thousands of cases annually with significant mortality.

    **Why repurposing matters:** While antibiotics help if caught early,
    severe cases progress rapidly. New therapeutic options could reduce
    mortality in late-stage disease.
    """)

st.divider()

# ─────────────────────────────────────────────────────────────
# Section 2, Protein Target Cards
# ─────────────────────────────────────────────────────────────
st.header("Protein Targets")
st.markdown(
    "Each disease is attacked through specific viral or bacterial proteins "
    "essential for pathogen survival. We dock drug candidates against these "
    "structures to find potential inhibitors."
)

# Role descriptions for each target
TARGET_ROLES: dict[str, str] = {
    "DENV_NS3": (
        "Cleaves the viral polyprotein into functional components. "
        "Essential for dengue virus replication, blocking this enzyme "
        "halts the viral life cycle."
    ),
    "DENV_NS5": (
        "RNA-dependent RNA polymerase that copies the viral genome. "
        "The primary replication engine of dengue virus and a "
        "high-priority drug target."
    ),
    "DENV_E": (
        "Mediates host cell entry through membrane fusion. "
        "Inhibiting this protein could prevent the virus from "
        "infecting new cells."
    ),
    "CHIKV_nsP2": (
        "Processes the nonstructural polyprotein of chikungunya virus. "
        "Critical for viral replication and a validated drug target."
    ),
    "CHIKV_nsP1": (
        "Caps viral mRNA to enable translation by host ribosomes. "
        "A unique enzymatic activity that makes it an attractive "
        "target for selective inhibitors."
    ),
    "LEPTO_LipL32": (
        "Outer membrane lipoprotein that triggers the host immune "
        "response. The most abundant surface protein of pathogenic "
        "Leptospira and a key virulence factor."
    ),
}

# Display targets grouped by disease
for disease_name, disease_info in DISEASES.items():
    target_keys = disease_info["targets"]
    priority = disease_info["priority"]

    st.subheader(f"{disease_name}  ·  {priority} Target")

    cols = st.columns(min(len(target_keys), 3))
    for i, target_id in enumerate(target_keys):
        info = TARGET_PROTEINS[target_id]
        with cols[i]:
            st.markdown(f"**{info['name']}**")
            st.caption(
                f"PDB: [{info['pdb_id']}](https://www.rcsb.org/structure/{info['pdb_id']})  ·  "
                f"UniProt: [{info['uniprot_id']}](https://www.uniprot.org/uniprot/{info['uniprot_id']})"
            )
            st.markdown(
                f"<p style='font-size:0.9em;'>{TARGET_ROLES.get(target_id, '')}</p>",
                unsafe_allow_html=True,
            )
            with st.spinner(f"Loading {info['pdb_id']}..."):
                render_protein(info["pdb_id"], width=350, height=300)

st.divider()

# ─────────────────────────────────────────────────────────────
# Section 3, Pipeline Overview
# ─────────────────────────────────────────────────────────────
st.header("Pipeline Overview")
st.markdown(
    "GeneTropica uses a five-stage hybrid pipeline combining classical "
    "molecular docking with modern AI techniques."
)

# Pipeline stages as a visual flow using columns
stages = [
    ("1. Data Acquisition", "📥", "Gather FDA-approved drug structures from DrugBank/ZINC15 and protein targets from RCSB PDB."),
    ("2. Structure Prediction", "🧠", "Predict 3D protein structures using ESMFold where experimental structures are unavailable."),
    ("3. Molecular Docking", "🔗", "Simulate drug-protein binding with AutoDock Vina to estimate binding affinity."),
    ("4. AI Scoring", "🤖", "ML rescoring with Random Forest, ADMET toxicity prediction, and PubMed literature mining."),
    ("5. Dashboard", "📊", "Interactive Streamlit app with 3D visualization, ranked candidates, and evidence."),
]

for i, (title, icon, desc) in enumerate(stages):
    c_icon, c_text = st.columns([0.08, 0.92])
    with c_icon:
        st.markdown(f"<h2 style='margin:0;'>{icon}</h2>", unsafe_allow_html=True)
    with c_text:
        st.markdown(f"**{title}**")
        st.markdown(desc)
    if i < len(stages) - 1:
        st.markdown(
            "<div style='text-align:center;color:#1B4F72;font-size:1.3em;'>↓</div>",
            unsafe_allow_html=True,
        )

st.divider()
st.caption("Data sources: RCSB PDB, DrugBank, ZINC15, PubMed, WHO, Indonesian Ministry of Health")
st.caption(
    "GeneTropica v2, Disease Overview | Russell Young, British School Jakarta"
)
