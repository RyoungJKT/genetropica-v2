"""Plotly chart builders for the dashboard."""

import numpy as np
import plotly.express as px
import plotly.graph_objects as go

from src.utils.db import (
    _query_df,
    get_drug_admet,
    get_drug_scores,
    get_drugs_for_target,
)

# Editorial palette matching the dashboard theme
THEME_PRIMARY = "#1F5740"
THEME_SECONDARY = "#A8742C"
THEME_ACCENT = "#2E7D5B"
THEME_DANGER = "#A8492B"

# Apply an editorial Plotly template globally: transparent canvas so charts sit on
# the paper background, brand fonts, and faint paper-toned gridlines.
import plotly.io as pio

pio.templates["genetropica"] = go.layout.Template(
    layout=dict(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Hanken Grotesk, system-ui, sans-serif", color="#1C1A17", size=13),
        title=dict(font=dict(family="Fraunces, Georgia, serif", size=18, color="#1C1A17")),
        xaxis=dict(gridcolor="#E2DAC8", linecolor="#D8D0BD", zerolinecolor="#E2DAC8"),
        yaxis=dict(gridcolor="#E2DAC8", linecolor="#D8D0BD", zerolinecolor="#E2DAC8"),
        colorway=["#1F5740", "#A8742C", "#2E7D5B", "#A8492B", "#544F45"],
        polar=dict(bgcolor="rgba(0,0,0,0)"),
    )
)
pio.templates.default = "genetropica"


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
        margin=dict(l=10, r=10, t=80, b=10),
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
        fillcolor="rgba(31, 87, 64, 0.16)",
        line_color=THEME_PRIMARY,
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
    """Distribution histogram of ligand efficiency for drug-like candidates.

    Args:
        target_id: Target to show distribution for.

    Returns:
        Plotly Figure.
    """
    df = get_drugs_for_target(target_id)
    if df.empty:
        return _empty_figure("No data available")

    dl = df[df["is_druglike"] == 1]
    vals = dl["ligand_efficiency"].dropna()
    counts, edges = np.histogram(vals, bins=20)
    centers = (edges[:-1] + edges[1:]) / 2
    bin_width = (edges[1] - edges[0]) if len(edges) > 1 else 1.0
    # Pre-binned bar (rather than px.histogram) so the bars can animate from zero.
    fig = go.Figure(
        go.Bar(
            x=centers,
            y=counts,
            width=bin_width,
            marker_color=THEME_PRIMARY,
            marker_line_width=0,
        )
    )
    fig.update_layout(
        title="Ligand-Efficiency Distribution (drug-like)",
        xaxis_title="Ligand Efficiency",
        yaxis_title="Number of Drugs",
        bargap=0,
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

    top = df[df["is_druglike"] == 1].sort_values(
        "ligand_efficiency", ascending=False
    ).head(n).copy()
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
        x=top["ligand_efficiency"],
        orientation="h",
        marker_color=colors,
        text=top["ligand_efficiency"].round(3),
        textposition="outside",
    ))
    fig.update_layout(
        title=f"Top {n} Drug-like Candidates by Ligand Efficiency",
        xaxis_title="Ligand Efficiency",
        height=max(300, n * 35),
        margin=dict(l=10, r=10, t=40, b=10),
    )
    return fig


def vina_vs_ml_scatter(target_id: str) -> go.Figure:
    """Scatter plot of Vina score vs ML score for all drugs against a target.

    Points colored by ADMET pass/fail, sized by literature evidence count,
    with the top-10 drug-like candidates by Vina rank highlighted.
    """
    df = get_drugs_for_target(target_id)
    if df.empty:
        return _empty_figure("No data available")

    df["admet_label"] = df["overall_pass"].map({1: "ADMET Pass", 0: "ADMET Fail"})
    df["is_top10"] = df["vina_rank"] <= 10
    # Ensure lit_count sizing is visible (min size 4)
    df["marker_size"] = df["lit_count"].clip(lower=0) + 4

    fig = go.Figure()

    # Non-top-10 ADMET pass
    mask_pass = (df["admet_label"] == "ADMET Pass") & (~df["is_top10"])
    fig.add_trace(go.Scatter(
        x=df.loc[mask_pass, "vina_score"],
        y=df.loc[mask_pass, "ml_binding_score"],
        mode="markers",
        marker=dict(
            size=df.loc[mask_pass, "marker_size"],
            color=THEME_ACCENT,
            opacity=0.6,
        ),
        text=df.loc[mask_pass, "name"],
        name="ADMET Pass",
        hovertemplate="%{text}<br>Vina: %{x:.2f}<br>ML: %{y:.2f}<extra></extra>",
    ))

    # Non-top-10 ADMET fail
    mask_fail = (df["admet_label"] == "ADMET Fail") & (~df["is_top10"])
    fig.add_trace(go.Scatter(
        x=df.loc[mask_fail, "vina_score"],
        y=df.loc[mask_fail, "ml_binding_score"],
        mode="markers",
        marker=dict(
            size=df.loc[mask_fail, "marker_size"],
            color=THEME_DANGER,
            opacity=0.6,
        ),
        text=df.loc[mask_fail, "name"],
        name="ADMET Fail",
        hovertemplate="%{text}<br>Vina: %{x:.2f}<br>ML: %{y:.2f}<extra></extra>",
    ))

    # Top 10 candidates, larger, outlined
    top10 = df[df["is_top10"]]
    fig.add_trace(go.Scatter(
        x=top10["vina_score"],
        y=top10["ml_binding_score"],
        mode="markers+text",
        marker=dict(
            size=14,
            color=THEME_PRIMARY,
            line=dict(width=2, color="white"),
            symbol="diamond",
        ),
        text=top10["name"],
        textposition="top center",
        textfont=dict(size=9),
        name="Top 10 (Vina rank)",
        hovertemplate="%{text}<br>Vina: %{x:.2f}<br>ML prior: %{y:.2f}<br>Vina rank: #%{customdata}<extra></extra>",
        customdata=top10["vina_rank"],
    ))

    # Diagonal reference line (perfect correlation)
    all_scores = list(df["vina_score"]) + list(df["ml_binding_score"])
    line_min, line_max = min(all_scores), max(all_scores)
    fig.add_trace(go.Scatter(
        x=[line_min, line_max],
        y=[line_min, line_max],
        mode="lines",
        line=dict(dash="dash", color="#C2BAA6", width=1),
        name="Perfect Correlation",
        showlegend=True,
    ))

    fig.update_layout(
        title="Vina Score vs ML Score",
        xaxis_title="Vina Score (kcal/mol)",
        yaxis_title="ML Binding Score (kcal/mol)",
        height=500,
        margin=dict(l=10, r=10, t=80, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    return fig


def admet_overview_bars() -> go.Figure:
    """Grouped bar chart showing pass/fail rates per ADMET property."""
    df = _query_df("""
        SELECT
            SUM(lipinski_pass) AS lipinski_pass,
            COUNT(*) - SUM(lipinski_pass) AS lipinski_fail,
            SUM(CASE WHEN hepatotoxicity_risk < 0.5 THEN 1 ELSE 0 END) AS hepato_safe,
            SUM(CASE WHEN hepatotoxicity_risk >= 0.5 THEN 1 ELSE 0 END) AS hepato_risk,
            SUM(CASE WHEN herg_inhibition_risk < 0.5 THEN 1 ELSE 0 END) AS herg_safe,
            SUM(CASE WHEN herg_inhibition_risk >= 0.5 THEN 1 ELSE 0 END) AS herg_risk,
            SUM(overall_pass) AS overall_pass,
            COUNT(*) - SUM(overall_pass) AS overall_fail
        FROM admet
    """)
    if df.empty:
        return _empty_figure("No ADMET data available")

    r = df.iloc[0]
    categories = ["Lipinski", "Hepatotoxicity", "hERG Inhibition", "Overall"]
    pass_vals = [int(r["lipinski_pass"]), int(r["hepato_safe"]), int(r["herg_safe"]), int(r["overall_pass"])]
    fail_vals = [int(r["lipinski_fail"]), int(r["hepato_risk"]), int(r["herg_risk"]), int(r["overall_fail"])]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=categories, y=pass_vals,
        name="Pass / Safe",
        marker_color=THEME_ACCENT,
        text=pass_vals, textposition="auto",
    ))
    fig.add_trace(go.Bar(
        x=categories, y=fail_vals,
        name="Fail / Risk",
        marker_color=THEME_DANGER,
        text=fail_vals, textposition="auto",
    ))
    fig.update_layout(
        title="ADMET Pass/Fail Breakdown",
        yaxis_title="Number of Drugs",
        barmode="group",
        height=350,
        margin=dict(l=10, r=10, t=80, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    return fig


def literature_bar(target_id: str, n: int = 15) -> go.Figure:
    """Bar chart of literature reference count per top drug for a target.

    Args:
        target_id: Target to filter by.
        n: Max number of drugs to show.
    """
    df = get_drugs_for_target(target_id)
    if df.empty:
        return _empty_figure("No data available")

    # Only drugs with at least one reference, sorted by count
    with_lit = df[df["lit_count"] > 0].sort_values("lit_count", ascending=False).head(n)
    if with_lit.empty:
        return _empty_figure("No literature evidence for this target")

    with_lit = with_lit.iloc[::-1]  # reverse for horizontal bar

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=with_lit["name"],
        x=with_lit["lit_count"],
        orientation="h",
        marker_color=THEME_SECONDARY,
        text=with_lit["lit_count"].astype(int),
        textposition="outside",
    ))
    fig.update_layout(
        title="Literature References per Drug",
        xaxis_title="Number of PubMed References",
        height=max(250, len(with_lit) * 30),
        margin=dict(l=10, r=10, t=40, b=10),
    )
    return fig


def novel_discoveries_highlight(target_id: str, n: int = 10) -> go.Figure:
    """Highlight drug-like candidates with strong ligand efficiency but zero literature.

    These represent potential novel leads, computationally promising,
    drug-like candidates that have not been studied for this target.
    """
    df = get_drugs_for_target(target_id)
    if df.empty:
        return _empty_figure("No data available")

    novels = df[(df["lit_count"] == 0) & (df["is_druglike"] == 1)].sort_values(
        "ligand_efficiency", ascending=False
    ).head(n).copy()

    if novels.empty:
        return _empty_figure("All top candidates have literature support")

    novels = novels.iloc[::-1]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=novels["name"],
        x=novels["ligand_efficiency"],
        orientation="h",
        marker_color=[
            "#A8742C" if row["overall_pass"] else "#C99A5B"
            for _, row in novels.iterrows()
        ],
        text=[
            f"{row['ligand_efficiency']:.3f} {'(ADMET safe)' if row['overall_pass'] else ''}"
            for _, row in novels.iterrows()
        ],
        textposition="outside",
    ))
    fig.update_layout(
        title="Novel Lead Candidates (drug-like, no prior literature)",
        xaxis_title="Ligand Efficiency",
        height=max(250, len(novels) * 30),
        margin=dict(l=10, r=50, t=40, b=10),
    )
    return fig


# ---------------------------------------------------------------------------
# MD Simulation Charts
# ---------------------------------------------------------------------------

MD_DRUG_COLORS = {
    "celecoxib": "#A8492B",
    "methotrexate": "#A8742C",
    "dasabuvir": "#1F5740",
}

MD_DRUG_LABELS = {
    "celecoxib": "Celecoxib (#1)",
    "methotrexate": "Methotrexate (#3)",
    "dasabuvir": "Dasabuvir (#17)",
}


def md_timeseries(
    data: dict,
    x_col: str,
    y_col: str,
    title: str,
    yaxis_title: str,
    smooth_window: int = 0,
) -> go.Figure:
    """Interactive Plotly line chart for MD time-series data.

    Args:
        data: Dict mapping drug name → DataFrame.
        x_col: Column name for x-axis (e.g. 'time_ns').
        y_col: Column name for y-axis (e.g. 'protein_rmsd_A').
        title: Chart title.
        yaxis_title: Y-axis label.
        smooth_window: If > 0, apply rolling average.
    """
    fig = go.Figure()
    for drug, df in data.items():
        y_vals = df[y_col]
        x_vals = df[x_col]
        if smooth_window > 0 and len(y_vals) > smooth_window:
            y_vals = y_vals.rolling(window=smooth_window, min_periods=1).mean()
        fig.add_trace(go.Scatter(
            x=x_vals,
            y=y_vals,
            mode="lines",
            name=MD_DRUG_LABELS.get(drug, drug.capitalize()),
            line=dict(color=MD_DRUG_COLORS.get(drug, "#888"), width=1.5),
            opacity=0.85,
        ))
    fig.update_layout(
        title=title,
        xaxis_title="Time (ns)",
        yaxis_title=yaxis_title,
        height=400,
        margin=dict(l=10, r=10, t=50, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        hovermode="x unified",
    )
    return fig


def md_bar_comparison(
    labels: list,
    values: list,
    errors: list | None,
    title: str,
    yaxis_title: str,
) -> go.Figure:
    """Plotly bar chart comparing a metric across 3 drugs.

    Args:
        labels: Drug names.
        values: Metric values.
        errors: Standard deviations (or None).
        title: Chart title.
        yaxis_title: Y-axis label.
    """
    colors = [MD_DRUG_COLORS.get(d.lower(), "#888") for d in labels]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=[MD_DRUG_LABELS.get(d.lower(), d) for d in labels],
        y=values,
        error_y=dict(type="data", array=errors, visible=True) if errors else None,
        marker_color=colors,
        text=[f"{v:.2f}" for v in values],
        textposition="outside",
    ))
    fig.update_layout(
        title=title,
        yaxis_title=yaxis_title,
        height=350,
        margin=dict(l=10, r=10, t=50, b=10),
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
        font=dict(size=14, color="#8A8273"),
    )
    fig.update_layout(
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        height=200,
    )
    return fig
