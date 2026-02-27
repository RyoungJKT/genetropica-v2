"""Plotly chart builders for the dashboard."""

import plotly.express as px
import plotly.graph_objects as go

from src.utils.db import get_drug_admet, get_drug_scores, get_drugs_for_target

# Consistent color palette matching the Streamlit theme
THEME_PRIMARY = "#1B4F72"
THEME_SECONDARY = "#2E86C1"
THEME_ACCENT = "#27AE60"
THEME_DANGER = "#E74C3C"


def score_comparison_bar(drug_id: str) -> go.Figure:
    """Horizontal bar chart showing a drug's scores across all targets.

    Args:
        drug_id: The drug to chart.

    Returns:
        Plotly Figure.
    """
    df = get_drug_scores(drug_id)
    if df.empty:
        return _empty_figure("No score data available")

    # Create label combining target name and disease
    df["label"] = df["target_name"] + " (" + df["disease"] + ")"

    fig = go.Figure()

    # Vina scores (negative = better, so we show absolute values)
    fig.add_trace(go.Bar(
        y=df["label"],
        x=df["vina_score"].abs(),
        name="Vina |score|",
        orientation="h",
        marker_color=THEME_PRIMARY,
        text=df["vina_score"].round(2),
        textposition="auto",
    ))

    fig.add_trace(go.Bar(
        y=df["label"],
        x=df["ml_binding_score"].abs(),
        name="ML |score|",
        orientation="h",
        marker_color=THEME_SECONDARY,
        text=df["ml_binding_score"].round(2),
        textposition="auto",
    ))

    fig.update_layout(
        title="Binding Scores Across Targets",
        xaxis_title="Absolute Binding Score (kcal/mol)",
        barmode="group",
        height=350,
        margin=dict(l=10, r=10, t=40, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    return fig


def admet_radar(drug_id: str) -> go.Figure:
    """Radar/spider chart showing ADMET safety profile.

    Args:
        drug_id: The drug to chart.

    Returns:
        Plotly Figure.
    """
    admet = get_drug_admet(drug_id)
    if admet is None:
        return _empty_figure("No ADMET data available")

    categories = [
        "Oral Bioavailability",
        "Lipinski Compliance",
        "Hepato Safety",
        "hERG Safety",
        "Overall Safety",
    ]
    # Convert to 0-1 scale where 1 = good
    values = [
        admet["oral_bioavailability"],
        1.0 if admet["lipinski_pass"] else 0.0,
        1.0 - admet["hepatotoxicity_risk"],
        1.0 - admet["herg_inhibition_risk"],
        1.0 if admet["overall_pass"] else 0.0,
    ]
    # Close the polygon
    values.append(values[0])
    categories.append(categories[0])

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=values,
        theta=categories,
        fill="toself",
        fillcolor="rgba(46, 134, 193, 0.25)",
        line_color=THEME_SECONDARY,
        name="ADMET Profile",
    ))
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
        title="ADMET Safety Profile",
        height=350,
        margin=dict(l=40, r=40, t=40, b=40),
        showlegend=False,
    )
    return fig


def score_distribution_histogram(target_id: str) -> go.Figure:
    """Distribution histogram of consensus scores for a target.

    Args:
        target_id: Target to show distribution for.

    Returns:
        Plotly Figure.
    """
    df = get_drugs_for_target(target_id)
    if df.empty:
        return _empty_figure("No data available")

    fig = px.histogram(
        df,
        x="consensus_score",
        nbins=20,
        color_discrete_sequence=[THEME_PRIMARY],
        labels={"consensus_score": "Consensus Score"},
    )
    fig.update_layout(
        title="Score Distribution",
        yaxis_title="Number of Drugs",
        height=300,
        margin=dict(l=10, r=10, t=40, b=10),
    )
    return fig


def top_candidates_bar(target_id: str, n: int = 10) -> go.Figure:
    """Horizontal bar chart of top N drug candidates for a target.

    Args:
        target_id: Target to rank drugs against.
        n: Number of top candidates to show.

    Returns:
        Plotly Figure.
    """
    df = get_drugs_for_target(target_id)
    if df.empty:
        return _empty_figure("No data available")

    top = df.head(n).copy()
    # Reverse for horizontal bar (top candidate at top of chart)
    top = top.iloc[::-1]

    # Color by ADMET pass/fail
    colors = [
        THEME_ACCENT if row["overall_pass"] else THEME_DANGER
        for _, row in top.iterrows()
    ]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=top["name"],
        x=top["consensus_score"],
        orientation="h",
        marker_color=colors,
        text=top["consensus_score"].round(3),
        textposition="outside",
    ))
    fig.update_layout(
        title=f"Top {n} Candidates",
        xaxis_title="Consensus Score",
        height=max(300, n * 35),
        margin=dict(l=10, r=10, t=40, b=10),
    )
    return fig


def _empty_figure(message: str) -> go.Figure:
    """Create a blank figure with a centered message."""
    fig = go.Figure()
    fig.add_annotation(
        text=message,
        xref="paper", yref="paper",
        x=0.5, y=0.5,
        showarrow=False,
        font=dict(size=14, color="#888"),
    )
    fig.update_layout(
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        height=200,
    )
    return fig
