"""ADMET Profiling dashboard page.

Drug-likeness filters, physicochemical radar, BOILED-Egg absorption
prediction, structural alerts, property heatmap, and top candidate
summary for all profiled drug candidates.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(layout="wide", initial_sidebar_state="expanded")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.components.layout import render_sidebar
from src.admet.profiles import load_profiles
from src.utils.db import get_connection

render_sidebar()

# Theme colours consistent with main dashboard
THEME_PRIMARY = "#1B4F72"
THEME_SECONDARY = "#2E86C1"
THEME_ACCENT = "#27AE60"
THEME_DANGER = "#E74C3C"

st.title("ADMET Profiling")
st.markdown(
    "Comprehensive absorption, distribution, metabolism, excretion, and "
    "toxicity analysis of all 50 drug candidates using RDKit-computed "
    "descriptors, rule-based filters, and BOILED-Egg absorption prediction."
)


# -----------------------------------------------------------------
# Load data
# -----------------------------------------------------------------

@st.cache_data(ttl=3600)
def _load_profiles() -> list[dict]:
    """Load precomputed ADMET profiles from JSON."""
    try:
        return load_profiles()
    except FileNotFoundError:
        return []


@st.cache_data(ttl=3600)
def _load_consensus_scores() -> pd.DataFrame:
    """Load average ligand efficiency per drug-like candidate from the database."""
    try:
        conn = get_connection()
        try:
            df = pd.read_sql_query(
                "SELECT d.name, AVG(m.ligand_efficiency) AS avg_score "
                "FROM ml_scores m "
                "JOIN drugs d ON m.drug_id = d.drug_id "
                "WHERE m.is_druglike = 1 "
                "GROUP BY d.name",
                conn,
            )
            return df
        finally:
            conn.close()
    except Exception:
        return pd.DataFrame()


profiles = _load_profiles()
consensus_df = _load_consensus_scores()

if not profiles:
    st.error(
        "ADMET profiles not found. Run the profiling script first: "
        "`python scripts/run_admet_profiling.py`"
    )
    st.stop()

total = len(profiles)


# -----------------------------------------------------------------
# Precompute aggregate counts
# -----------------------------------------------------------------

lipinski_pass = sum(1 for p in profiles if p["lipinski"]["pass"])
veber_pass = sum(1 for p in profiles if p["veber"]["pass"])
ghose_pass = sum(1 for p in profiles if p["ghose"]["pass"])
egan_pass = sum(1 for p in profiles if p["egan"]["pass"])
pains_clean = sum(1 for p in profiles if len(p["pains_alerts"]) == 0)
brenk_clean = sum(1 for p in profiles if len(p["brenk_alerts"]) == 0)
high_gi = sum(1 for p in profiles if p["gi_absorption"] == "High")
bbb_yes = sum(1 for p in profiles if p["bbb_permeant"] == "Yes")
low_abs = total - high_gi


# =================================================================
# Section 1, Drug-Likeness Filter Summary
# =================================================================
st.divider()
st.header("1. Drug-Likeness Filter Summary")
st.markdown(
    "Five rule-based filters assess whether each drug candidate has "
    "physicochemical properties consistent with oral bioavailability and "
    "an absence of problematic substructures."
)

# Metric cards
c1, c2, c3, c4, c5 = st.columns(5)

for col, label, passed in [
    (c1, "Lipinski", lipinski_pass),
    (c2, "Veber", veber_pass),
    (c3, "Ghose", ghose_pass),
    (c4, "Egan", egan_pass),
    (c5, "PAINS Clean", pains_clean),
]:
    with col:
        pct = passed / total * 100
        st.metric(label, f"{passed}/{total}", f"{pct:.0f}%")

# Bar chart of pass rates
filter_names = ["Lipinski", "Veber", "Ghose", "Egan", "PAINS Clean"]
filter_counts = [lipinski_pass, veber_pass, ghose_pass, egan_pass, pains_clean]
filter_pcts = [c / total * 100 for c in filter_counts]
bar_colors = [THEME_ACCENT if p >= 50 else THEME_DANGER for p in filter_pcts]

bar_fig = go.Figure(data=go.Bar(
    x=filter_names,
    y=filter_pcts,
    marker_color=bar_colors,
    text=[f"{p:.0f}%" for p in filter_pcts],
    textposition="outside",
))
bar_fig.update_layout(
    title="Drug-Likeness Filter Pass Rates",
    yaxis_title="Pass Rate (%)",
    yaxis=dict(range=[0, 110]),
    height=400,
    margin=dict(l=10, r=10, t=80, b=10),
)
st.plotly_chart(bar_fig, use_container_width=True)

# Expander with filter criteria table
with st.expander("Filter Criteria Reference"):
    st.markdown("""
    | Filter | Criteria | Purpose |
    |--------|----------|---------|
    | **Lipinski (Ro5)** | MW <= 500, LogP <= 5, HBD <= 5, HBA <= 10 | Oral bioavailability |
    | **Veber** | TPSA <= 140 A, Rotatable Bonds <= 10 | Oral bioavailability |
    | **Ghose** | MW 160-480, LogP -0.4 to 5.6, Atoms 20-70, MR 40-130 | Drug-like property range |
    | **Egan** | TPSA <= 132, LogP <= 5.88 | Passive GI absorption |
    | **PAINS** | No pan-assay interference substructures | Assay reliability |
    """)


# =================================================================
# Section 2, Physicochemical Radar
# =================================================================
st.divider()
st.header("2. Physicochemical Radar")
st.markdown(
    "Radar chart normalising each descriptor to its Lipinski/Veber limit. "
    "Values inside the dashed green circle (1.0) satisfy oral drug-likeness "
    "rules; values beyond it indicate potential liabilities."
)

drug_names_list = sorted([p["name"].capitalize() for p in profiles])
name_to_profile = {p["name"].capitalize(): p for p in profiles}

selected_name = st.selectbox(
    "Select Drug", options=drug_names_list, index=0, key="radar_drug"
)
sel = name_to_profile[selected_name]
desc = sel["descriptors"]

# Radar axes and normalisation limits
radar_labels = ["MW", "LogP", "TPSA", "HBD", "HBA", "RotBonds"]
radar_limits = [500, 5, 140, 5, 10, 10]  # Lipinski/Veber thresholds
radar_values_raw = [
    desc["mw"], desc["logp"], desc["tpsa"],
    desc["hbd"], desc["hba"], desc["rotatable_bonds"],
]
# Normalise: value / limit (clamp negatives for LogP)
radar_values = [max(v, 0) / lim for v, lim in zip(radar_values_raw, radar_limits)]

# Close the polygon
radar_labels_closed = radar_labels + [radar_labels[0]]
radar_values_closed = radar_values + [radar_values[0]]
limit_line = [1.0] * (len(radar_labels) + 1)

radar_fig = go.Figure()

# Ideal limit (dashed green)
radar_fig.add_trace(go.Scatterpolar(
    r=limit_line,
    theta=radar_labels_closed,
    mode="lines",
    name="Ideal Limit (1.0)",
    line=dict(color=THEME_ACCENT, width=2, dash="dash"),
    fill="none",
))

# Drug values (filled blue area)
radar_fig.add_trace(go.Scatterpolar(
    r=radar_values_closed,
    theta=radar_labels_closed,
    mode="lines+markers",
    name=selected_name,
    line=dict(color=THEME_SECONDARY, width=2),
    fill="toself",
    fillcolor="rgba(46, 134, 193, 0.25)",
    marker=dict(size=6),
))

radar_fig.update_layout(
    title=f"Physicochemical Radar - {selected_name}",
    polar=dict(radialaxis=dict(visible=True, range=[0, max(max(radar_values), 1.2) + 0.2])),
    height=450,
    margin=dict(l=40, r=40, t=80, b=40),
    showlegend=True,
    legend=dict(orientation="h", yanchor="bottom", y=-0.15),
)
st.plotly_chart(radar_fig, use_container_width=True)

# Descriptor metrics below radar
m1, m2, m3 = st.columns(3)
with m1:
    st.metric("Molecular Weight", f"{desc['mw']:.1f} Da")
    st.metric("HBD / HBA", f"{desc['hbd']} / {desc['hba']}")
with m2:
    st.metric("LogP", f"{desc['logp']:.2f}")
    st.metric("Rotatable Bonds", str(desc["rotatable_bonds"]))
with m3:
    st.metric("TPSA", f"{desc['tpsa']:.1f} A^2")
    st.metric("ESOL (LogS)", f"{sel['esol']:.2f}")

# Filter result badges
lip = sel["lipinski"]["pass"]
veb = sel["veber"]["pass"]
gho = sel["ghose"]["pass"]
ega = sel["egan"]["pass"]
pns = len(sel["pains_alerts"]) == 0

badge_md = "**Filter Results:** "
for fname, passed in [
    ("Lipinski", lip), ("Veber", veb), ("Ghose", gho),
    ("Egan", ega), ("PAINS Clean", pns),
]:
    icon = "Pass" if passed else "Fail"
    color = "green" if passed else "red"
    badge_md += f"&nbsp; :{color}[{fname}: {icon}]"

st.markdown(badge_md)


# =================================================================
# Section 3, BOILED-Egg Plot
# =================================================================
st.divider()
st.header("3. BOILED-Egg Absorption Plot")
st.markdown(
    "The BOILED-Egg model predicts gastrointestinal (GI) absorption and "
    "blood-brain barrier (BBB) penetration from LogP and TPSA. The white "
    "region indicates high GI absorption; the yellow yolk indicates "
    "probable BBB permeation."
)

# Classify each drug
egg_logp = [p["descriptors"]["logp"] for p in profiles]
egg_tpsa = [p["descriptors"]["tpsa"] for p in profiles]
egg_names = [p["name"].capitalize() for p in profiles]
egg_categories = []
egg_colors = []

for p in profiles:
    if p["bbb_permeant"] == "Yes":
        egg_categories.append("BBB Permeant")
        egg_colors.append("#F4D03F")  # gold
    elif p["gi_absorption"] == "High":
        egg_categories.append("High GI Absorption")
        egg_colors.append("#D5DBDB")  # light grey
    else:
        egg_categories.append("Low Absorption")
        egg_colors.append(THEME_DANGER)

egg_fig = go.Figure()

# GI absorption region (white of egg)
egg_fig.add_shape(
    type="rect",
    x0=-2.3, x1=6.8, y0=0, y1=142,
    fillcolor="rgba(213, 219, 219, 0.15)",
    line=dict(color="#AEB6BF", width=1.5, dash="dot"),
    layer="below",
)

# BBB yolk region
egg_fig.add_shape(
    type="rect",
    x0=-0.5, x1=5.0, y0=0, y1=79,
    fillcolor="rgba(244, 208, 63, 0.15)",
    line=dict(color="#F4D03F", width=1.5, dash="dot"),
    layer="below",
)

# Region labels
egg_fig.add_annotation(
    x=6.5, y=135, text="GI Absorption Region",
    showarrow=False, font=dict(size=10, color="#7F8C8D"),
)
egg_fig.add_annotation(
    x=4.7, y=73, text="BBB Yolk Region",
    showarrow=False, font=dict(size=10, color="#B7950B"),
)

# Plot drug points by category
for cat, color, symbol in [
    ("BBB Permeant", "#F4D03F", "circle"),
    ("High GI Absorption", "#AEB6BF", "diamond"),
    ("Low Absorption", THEME_DANGER, "x"),
]:
    idx = [i for i, c in enumerate(egg_categories) if c == cat]
    if not idx:
        continue
    egg_fig.add_trace(go.Scatter(
        x=[egg_logp[i] for i in idx],
        y=[egg_tpsa[i] for i in idx],
        mode="markers+text",
        name=cat,
        text=[egg_names[i] for i in idx],
        textposition="top center",
        textfont=dict(size=8),
        marker=dict(size=10, color=color, symbol=symbol, line=dict(width=1, color="#333")),
    ))

egg_fig.update_layout(
    title="BOILED-Egg: GI Absorption and BBB Penetration",
    xaxis_title="LogP",
    yaxis_title="TPSA (A^2)",
    height=550,
    margin=dict(l=10, r=10, t=80, b=10),
    legend=dict(orientation="h", yanchor="bottom", y=-0.18),
)
st.plotly_chart(egg_fig, use_container_width=True)

# Metrics
ec1, ec2, ec3 = st.columns(3)
with ec1:
    st.metric("High GI Absorption", f"{high_gi}/{total}")
with ec2:
    st.metric("BBB Permeant", f"{bbb_yes}/{total}")
with ec3:
    st.metric("Low Absorption", f"{low_abs}/{total}")


# =================================================================
# Section 4, Structural Alerts
# =================================================================
st.divider()
st.header("4. Structural Alerts")
st.markdown(
    "PAINS (pan-assay interference compounds) and Brenk filters flag "
    "substructures associated with assay artefacts or chemical instability."
)

alert_rows = []
for p in profiles:
    pains = p["pains_alerts"]
    brenk = p["brenk_alerts"]
    if pains or brenk:
        alert_rows.append({
            "Drug": p["name"].capitalize(),
            "PAINS Alerts": ", ".join(pains) if pains else "None",
            "Brenk Alerts": ", ".join(brenk) if brenk else "None",
        })

if alert_rows:
    st.dataframe(
        pd.DataFrame(alert_rows),
        use_container_width=True,
        hide_index=True,
    )
else:
    st.success("All drugs are free of PAINS and Brenk structural alerts.")

ac1, ac2 = st.columns(2)
with ac1:
    st.metric("PAINS Clean", f"{pains_clean}/{total}")
with ac2:
    st.metric("Brenk Clean", f"{brenk_clean}/{total}")


# =================================================================
# Section 5, ADMET Property Heatmap
# =================================================================
st.divider()
st.header("5. ADMET Property Heatmap")
st.markdown(
    "Binary pass/fail matrix across eight ADMET criteria for all profiled "
    "drugs. Green cells indicate a pass; red cells indicate a fail."
)

# Build matrix
heatmap_cols = [
    "Lipinski", "Veber", "Ghose", "Egan",
    "PAINS Clean", "Brenk Clean", "GI Absorption", "BBB Permeant",
]

sorted_profiles = sorted(profiles, key=lambda p: p["name"])
drug_labels = [p["name"].capitalize() for p in sorted_profiles]

z_matrix = []
for p in sorted_profiles:
    row = [
        int(p["lipinski"]["pass"]),
        int(p["veber"]["pass"]),
        int(p["ghose"]["pass"]),
        int(p["egan"]["pass"]),
        int(len(p["pains_alerts"]) == 0),
        int(len(p["brenk_alerts"]) == 0),
        int(p["gi_absorption"] == "High"),
        int(p["bbb_permeant"] == "Yes"),
    ]
    z_matrix.append(row)

# Custom green/red colour scale
hm_colorscale = [[0, THEME_DANGER], [1, THEME_ACCENT]]

# Text annotations
hm_text = [["Pass" if v == 1 else "Fail" for v in row] for row in z_matrix]

hm_fig = go.Figure(data=go.Heatmap(
    z=z_matrix,
    x=heatmap_cols,
    y=drug_labels,
    colorscale=hm_colorscale,
    zmin=0,
    zmax=1,
    text=hm_text,
    texttemplate="%{text}",
    textfont=dict(size=10),
    showscale=False,
))

hm_height = max(400, total * 22)
hm_fig.update_layout(
    title="ADMET Property Matrix",
    height=hm_height,
    margin=dict(l=10, r=10, t=80, b=10),
    xaxis=dict(side="top"),
    yaxis=dict(autorange="reversed"),
)
st.plotly_chart(hm_fig, use_container_width=True)


# =================================================================
# Section 6, Top Candidates Summary
# =================================================================
st.divider()
st.header("6. Top Candidates Summary")
st.markdown(
    "Ranked summary of all profiled drugs by drug-likeness score (0-5). "
    "Higher scores indicate compliance with more rule-based filters."
)

# Build summary DataFrame
summary_rows = []
for p in profiles:
    n_alerts = len(p["pains_alerts"]) + len(p["brenk_alerts"])
    summary_rows.append({
        "Drug": p["name"].capitalize(),
        "DL Score": p["drug_likeness_score"],
        "MW": round(p["descriptors"]["mw"], 1),
        "LogP": round(p["descriptors"]["logp"], 2),
        "TPSA": round(p["descriptors"]["tpsa"], 1),
        "ESOL": round(p["esol"], 2),
        "GI": p["gi_absorption"],
        "BBB": p["bbb_permeant"],
        "Alerts": n_alerts,
    })

summary_df = pd.DataFrame(summary_rows).sort_values("DL Score", ascending=False)

# Merge consensus scores if available
if not consensus_df.empty:
    consensus_df_cap = consensus_df.copy()
    consensus_df_cap["Drug"] = consensus_df_cap["name"].str.capitalize()
    summary_df = summary_df.merge(
        consensus_df_cap[["Drug", "avg_score"]],
        on="Drug",
        how="left",
    )
    summary_df.rename(columns={"avg_score": "Avg Ligand Eff."}, inplace=True)

st.dataframe(
    summary_df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "DL Score": st.column_config.ProgressColumn(
            "DL Score",
            min_value=0,
            max_value=5,
            format="%d/5",
        ),
        "MW": st.column_config.NumberColumn(format="%.1f"),
        "LogP": st.column_config.NumberColumn(format="%.2f"),
        "TPSA": st.column_config.NumberColumn(format="%.1f"),
        "ESOL": st.column_config.NumberColumn(format="%.2f"),
    },
)

# Metrics
score5 = sum(1 for p in profiles if p["drug_likeness_score"] == 5)
score4plus = sum(1 for p in profiles if p["drug_likeness_score"] >= 4)
sm1, sm2, sm3 = st.columns(3)
with sm1:
    st.metric("Perfect Score (5/5)", f"{score5}")
with sm2:
    st.metric("Strong Candidates (4+/5)", f"{score4plus}")
with sm3:
    st.metric("Total Profiled", f"{total}")


# =================================================================
# Interpretation
# =================================================================
st.divider()
st.header("Interpretation")

st.markdown(f"""
The ADMET profiling analysis evaluated **{total}** drug candidates across
five drug-likeness filters and two absorption models:

- **Lipinski Rule of Five** was satisfied by **{lipinski_pass}** drugs
  ({lipinski_pass/total*100:.0f}%), confirming the majority of candidates
  have molecular properties consistent with oral bioavailability.
- **{high_gi}** out of {total} drugs are predicted to have **high GI
  absorption**, and **{bbb_yes}** are predicted to cross the blood-brain
  barrier (relevant for neurotropic infections like Dengue encephalitis).
- **{pains_clean}** drugs passed the **PAINS** filter and **{brenk_clean}**
  passed the **Brenk** structural alert screen, indicating that the
  majority of candidates are free of substructures commonly associated
  with assay interference or chemical instability.
- **{score5}** candidates achieved a perfect drug-likeness score of 5/5,
  and **{score4plus}** scored 4 or above, representing the strongest
  candidates for further investigation.

Overall, the repurposing library demonstrates favourable ADMET
characteristics, which is expected given that these are approved drugs
with established pharmacokinetic profiles. The BOILED-Egg analysis
highlights candidates with optimal absorption and distribution
properties for the intended therapeutic targets.
""")


# -----------------------------------------------------------------
# Footer
# -----------------------------------------------------------------
st.divider()
st.caption(
    "GeneTropica v2, ADMET Profiling | Russell Young, British School Jakarta"
)
