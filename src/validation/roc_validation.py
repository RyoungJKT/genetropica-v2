"""ROC curve and enrichment factor analysis for screening validation.

Computes ROC curves, AUC-ROC, and enrichment factors for three
scoring methods: docking only (Vina), GNN only, and consensus.
Generates interactive Plotly plots and summary reports.

Supports both mock scores (for rapid testing) and real docking-based
validation against DENV NS5 RdRp (PDB: 5CCV).
"""

import json
import logging
import tempfile
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from sklearn.metrics import roc_auc_score, roc_curve

from src.utils.config import BASE_DIR
from src.validation.collect_actives import KNOWN_ACTIVES

logger = logging.getLogger(__name__)

ROC_RESULTS_DIR: Path = BASE_DIR / "data" / "validation" / "roc_results"

# Theme colours consistent with the main dashboard
THEME_PRIMARY = "#1B4F72"
THEME_SECONDARY = "#2E86C1"
THEME_ACCENT = "#27AE60"
THEME_DANGER = "#E74C3C"
THEME_WARNING = "#F39C12"


# ─── Core metrics ─────────────────────────────────────────────


def compute_roc(
    labels: list[int],
    scores: list[float],
) -> dict:
    """Compute ROC curve and AUC for a set of labels and scores.

    Args:
        labels: Binary labels (1 = active, 0 = decoy).
        scores: Predicted scores (higher = more likely active).

    Returns:
        Dict with keys: auc, fpr (list), tpr (list), thresholds (list).
    """
    labels_arr = np.array(labels, dtype=int)
    scores_arr = np.array(scores, dtype=float)

    fpr, tpr, thresholds = roc_curve(labels_arr, scores_arr)
    auc = roc_auc_score(labels_arr, scores_arr)

    return {
        "auc": round(float(auc), 4),
        "fpr": fpr.tolist(),
        "tpr": tpr.tolist(),
        "thresholds": thresholds.tolist(),
    }


def compute_enrichment_factors(
    labels: list[int],
    scores: list[float],
    thresholds: Optional[list[float]] = None,
) -> dict:
    """Compute enrichment factors at specified thresholds.

    EF(x%) = (n_actives_in_top_x% / n_top_x%) / (n_total_actives / n_total)

    Args:
        labels: Binary labels (1 = active, 0 = decoy).
        scores: Predicted scores (higher = more likely active).
        thresholds: Fraction thresholds (default: 1%, 5%, 10%).

    Returns:
        Dict with keys: ef_1pct, ef_5pct, ef_10pct.
    """
    if thresholds is None:
        thresholds = [0.01, 0.05, 0.10]

    labels_arr = np.array(labels, dtype=int)
    scores_arr = np.array(scores, dtype=float)

    # Sort by score descending (higher = better)
    sorted_indices = np.argsort(-scores_arr)
    sorted_labels = labels_arr[sorted_indices]

    n_total = len(labels_arr)
    n_actives = int(labels_arr.sum())

    if n_actives == 0 or n_total == 0:
        return {f"ef_{int(t*100)}pct": 0.0 for t in thresholds}

    fraction_active = n_actives / n_total
    result = {}

    for t in thresholds:
        n_top = max(1, int(np.ceil(n_total * t)))
        n_actives_in_top = int(sorted_labels[:n_top].sum())
        fraction_active_in_top = n_actives_in_top / n_top
        ef = fraction_active_in_top / fraction_active if fraction_active > 0 else 0.0
        result[f"ef_{int(t * 100)}pct"] = round(ef, 2)

    return result


# ─── Mock score generation ────────────────────────────────────


def generate_mock_validation_scores(seed: int = 42) -> dict:
    """Generate realistic mock validation scores.

    .. deprecated::
        Use :func:`run_real_validation` instead, which performs actual
        Vina docking and ML rescoring rather than sampling from
        synthetic distributions.  This function is retained only for
        rapid testing / offline development.

    Actives get systematically better scores than decoys, with
    realistic overlap to produce AUC ~0.78-0.85.

    Args:
        seed: Random seed for reproducibility.

    Returns:
        Dict with keys: actives (list of dicts), decoys (list of dicts).
    """
    rng = np.random.RandomState(seed)
    n_decoys = 200

    actives = []
    for compound in KNOWN_ACTIVES:
        # Active docking scores: stronger binding (more negative)
        docking = round(float(rng.normal(-8.5, 1.5)), 2)
        docking = min(docking, -3.0)  # cap at reasonable range

        # Active GNN scores: higher confidence
        gnn = round(float(np.clip(rng.normal(0.72, 0.12), 0.0, 1.0)), 3)

        # Consensus: 0.4 * normalized_docking + 0.6 * gnn
        # Normalize docking: map [-12, -3] to [1, 0]
        docking_norm = np.clip((docking + 3.0) / -9.0, 0.0, 1.0)
        consensus = round(float(0.4 * docking_norm + 0.6 * gnn), 4)

        actives.append({
            "name": compound["name"],
            "pubchem_cid": compound["pubchem_cid"],
            "is_active": True,
            "docking_score": docking,
            "gnn_score": gnn,
            "consensus_score": consensus,
        })

    decoys = []
    for i in range(n_decoys):
        # Decoy docking: weaker binding
        docking = round(float(rng.normal(-5.5, 1.5)), 2)
        docking = min(docking, -1.0)

        # Decoy GNN: lower scores
        gnn = round(float(np.clip(rng.normal(0.42, 0.15), 0.0, 1.0)), 3)

        docking_norm = np.clip((docking + 3.0) / -9.0, 0.0, 1.0)
        consensus = round(float(0.4 * docking_norm + 0.6 * gnn), 4)

        decoys.append({
            "name": f"DECOY_{i + 1:04d}",
            "is_active": False,
            "docking_score": docking,
            "gnn_score": gnn,
            "consensus_score": consensus,
        })

    return {"actives": actives, "decoys": decoys}


# ─── Real docking validation ─────────────────────────────────


def _prepare_single_ligand(name: str, smiles: str, output_dir: Path) -> Optional[Path]:
    """Prepare a single ligand PDBQT from SMILES.

    Generates 3D coordinates with RDKit ETKDG, then converts to PDBQT
    via Open Babel.  Mirrors the logic in prepare_ligands.py but
    operates on a single compound.

    Args:
        name: Compound identifier (used for filenames).
        smiles: SMILES string.
        output_dir: Directory for intermediate SDF and output PDBQT.

    Returns:
        Path to the PDBQT file, or None on failure.
    """
    from src.data_acquisition.prepare_ligands import convert_to_pdbqt, smiles_to_3d

    safe_name = name.lower().replace(" ", "_").replace("'", "").replace("-", "_")
    sdf_dir = output_dir / "sdf"
    pdbqt_dir = output_dir / "pdbqt"
    sdf_dir.mkdir(parents=True, exist_ok=True)
    pdbqt_dir.mkdir(parents=True, exist_ok=True)

    sdf_path = sdf_dir / f"{safe_name}.sdf"
    pdbqt_path = pdbqt_dir / f"{safe_name}.pdbqt"

    if pdbqt_path.exists():
        return pdbqt_path

    if not sdf_path.exists():
        if not smiles_to_3d(smiles, sdf_path):
            logger.warning("3D generation failed for %s", name)
            return None

    if not convert_to_pdbqt(sdf_path, pdbqt_path):
        logger.warning("PDBQT conversion failed for %s", name)
        return None

    return pdbqt_path


def run_real_validation(
    output_dir: Optional[Path] = None,
    exhaustiveness: int = 8,
) -> dict:
    """Run validation with real Vina docking and ML rescoring.

    Docks the 8 known RdRp inhibitors and ~200+ property-matched
    decoys against DENV NS5 (PDB 5CCV), applies ML rescoring, and
    computes ROC / enrichment metrics for all three scoring methods.

    Args:
        output_dir: Directory for results.  Defaults to ROC_RESULTS_DIR.
        exhaustiveness: Vina exhaustiveness parameter.

    Returns:
        Dict with per-method ROC/EF results, metadata, and verdict,
        compatible with :func:`load_validation_results`.
    """
    from src.docking.prepare_receptor import prepare_receptor, define_search_box
    from src.docking.run_vina import dock_single
    from src.ai_scoring.ml_rescore import rescore_single
    from src.validation.generate_decoys import generate_decoys_for_active

    out = output_dir or ROC_RESULTS_DIR
    out.mkdir(parents=True, exist_ok=True)

    target_id = "DENV_NS5"

    # ── 1. Prepare receptor ──────────────────────────────────
    logger.info("Preparing receptor for %s ...", target_id)
    receptor_pdbqt = prepare_receptor(target_id)
    if receptor_pdbqt is None:
        raise RuntimeError(
            f"Receptor preparation failed for {target_id}. "
            "Ensure the PDB file exists in data/structures/."
        )
    search_box = define_search_box(target_id)

    # ── 2. Generate decoys ───────────────────────────────────
    logger.info("Generating property-matched decoys ...")
    decoy_smiles_set: set[str] = set()
    decoy_records: list[dict] = []

    for active in KNOWN_ACTIVES:
        # First pass: tighter parameters for harder decoys
        tight_decoys = generate_decoys_for_active(
            active["smiles"],
            n_decoys=40,
            seed=42,
            mw_tolerance=0.15,
            logp_tolerance=0.5,
            max_tanimoto=0.5,
        )
        for smi in tight_decoys:
            if smi not in decoy_smiles_set:
                decoy_smiles_set.add(smi)
                decoy_records.append({
                    "name": f"DECOY_{len(decoy_records) + 1:04d}",
                    "smiles": smi,
                    "source_active": active["name"],
                })

    # If fewer than 200 total decoys, do a second pass with standard params
    if len(decoy_records) < 200:
        logger.info(
            "Only %d decoys from tight params; filling with standard params ...",
            len(decoy_records),
        )
        for active in KNOWN_ACTIVES:
            if len(decoy_records) >= 200:
                break
            standard_decoys = generate_decoys_for_active(
                active["smiles"],
                n_decoys=30,
                seed=123,
                mw_tolerance=0.25,
                logp_tolerance=1.0,
                max_tanimoto=0.4,
            )
            for smi in standard_decoys:
                if smi not in decoy_smiles_set:
                    decoy_smiles_set.add(smi)
                    decoy_records.append({
                        "name": f"DECOY_{len(decoy_records) + 1:04d}",
                        "smiles": smi,
                        "source_active": active["name"],
                    })
                    if len(decoy_records) >= 200:
                        break

    logger.info("Total decoys generated: %d", len(decoy_records))

    # ── 3. Prepare ligand PDBQTs and dock ────────────────────
    with tempfile.TemporaryDirectory(prefix="genetropica_val_") as tmp_str:
        tmp = Path(tmp_str)
        ligand_dir = tmp / "ligands"
        dock_dir = tmp / "docking"
        ligand_dir.mkdir()
        dock_dir.mkdir()

        # Helper: dock a single compound, return scores dict or None
        def _dock_and_score(
            name: str, smiles: str, is_active: bool
        ) -> Optional[dict]:
            pdbqt = _prepare_single_ligand(name, smiles, ligand_dir)
            if pdbqt is None:
                logger.warning("Skipping %s — ligand preparation failed", name)
                return None

            result = dock_single(
                receptor_pdbqt,
                pdbqt,
                search_box,
                output_dir=dock_dir,
                exhaustiveness=exhaustiveness,
                n_poses=3,
            )
            if result is None or not result["scores"]:
                logger.warning("Skipping %s — docking failed", name)
                return None

            best_vina = result["scores"][0]

            # ML rescore
            ml_score = rescore_single(smiles, target_id, best_vina)
            if ml_score is None:
                logger.warning(
                    "ML rescoring failed for %s; using Vina-only consensus", name,
                )
                # Fallback: use Vina-normalised score as the ML component
                ml_score = round(
                    float(np.clip((best_vina + 4.0) / -8.0, 0.0, 1.0)), 4,
                )

            # Consensus: target-specific weights
            from src.ai_scoring.consensus_rank import get_target_weights
            vw, mw = get_target_weights(target_id)
            vina_norm = float(np.clip((best_vina + 4.0) / -8.0, 0.0, 1.0))
            consensus = round(vw * vina_norm + mw * ml_score, 4)

            return {
                "name": name,
                "is_active": is_active,
                "docking_score": round(best_vina, 2),
                "gnn_score": ml_score,
                "consensus_score": consensus,
            }

        # ── 3a. Dock actives ─────────────────────────────────
        actives_results: list[dict] = []
        n_actives_total = len(KNOWN_ACTIVES)
        for idx, compound in enumerate(KNOWN_ACTIVES, start=1):
            logger.info(
                "[Active %d/%d] Docking %s ...",
                idx, n_actives_total, compound["name"],
            )
            entry = _dock_and_score(
                compound["name"], compound["smiles"], is_active=True,
            )
            if entry is not None:
                entry["pubchem_cid"] = compound["pubchem_cid"]
                actives_results.append(entry)

        if not actives_results:
            raise RuntimeError("All actives failed to dock — cannot compute ROC.")

        logger.info(
            "Successfully docked %d / %d actives",
            len(actives_results), n_actives_total,
        )

        # ── 3b. Dock decoys ──────────────────────────────────
        decoys_results: list[dict] = []
        n_decoys_total = len(decoy_records)
        for idx, decoy in enumerate(decoy_records, start=1):
            if idx % 25 == 0 or idx == 1:
                logger.info(
                    "[Decoy %d/%d] Docking %s ...",
                    idx, n_decoys_total, decoy["name"],
                )
            entry = _dock_and_score(
                decoy["name"], decoy["smiles"], is_active=False,
            )
            if entry is not None:
                decoys_results.append(entry)

        logger.info(
            "Successfully docked %d / %d decoys",
            len(decoys_results), n_decoys_total,
        )

    if not decoys_results:
        raise RuntimeError("All decoys failed to dock — cannot compute ROC.")

    # ── 4. Assemble scores_data and compute metrics ──────────
    scores_data = {"actives": actives_results, "decoys": decoys_results}
    all_entries = actives_results + decoys_results

    labels = [1 if e["is_active"] else 0 for e in all_entries]

    # For docking: more negative = better, so negate for ROC (higher = better)
    docking_scores = [-e["docking_score"] for e in all_entries]
    gnn_scores = [e["gnn_score"] for e in all_entries]
    consensus_scores = [e["consensus_score"] for e in all_entries]

    summary: dict = {}
    for method_name, scores in [
        ("docking", docking_scores),
        ("gnn", gnn_scores),
        ("consensus", consensus_scores),
    ]:
        roc = compute_roc(labels, scores)
        ef = compute_enrichment_factors(labels, scores)
        summary[method_name] = {
            "auc": roc["auc"],
            "fpr": roc["fpr"],
            "tpr": roc["tpr"],
            **ef,
        }

    # Metadata
    summary["metadata"] = {
        "n_actives": sum(labels),
        "n_decoys": len(labels) - sum(labels),
        "n_total": len(labels),
        "target_pdb": "5CCV",
        "target_name": "DENV NS5 RdRp",
        "scoring": "real_docking",
        "exhaustiveness": exhaustiveness,
    }

    # Verdict
    consensus_auc = summary["consensus"]["auc"]
    if consensus_auc > 0.85:
        summary["verdict"] = "EXCELLENT"
    elif consensus_auc >= 0.70:
        summary["verdict"] = "GOOD"
    elif consensus_auc >= 0.60:
        summary["verdict"] = "ACCEPTABLE"
    else:
        summary["verdict"] = "POOR"

    # ── 5. Save results ──────────────────────────────────────
    _save_scores_csv(all_entries, "docking_score", out / "docking_scores.csv")
    _save_scores_csv(all_entries, "gnn_score", out / "gnn_scores.csv")
    _save_scores_csv(all_entries, "consensus_score", out / "consensus_scores.csv")

    summary_compact: dict = {}
    for key in ["docking", "gnn", "consensus"]:
        summary_compact[key] = {
            "auc": summary[key]["auc"],
            "ef_1pct": summary[key]["ef_1pct"],
            "ef_5pct": summary[key]["ef_5pct"],
            "ef_10pct": summary[key]["ef_10pct"],
        }
    summary_compact["metadata"] = summary["metadata"]
    summary_compact["verdict"] = summary["verdict"]

    summary_path = out / "validation_summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary_compact, f, indent=2)

    scores_path = out / "validation_scores.json"
    with open(scores_path, "w") as f:
        json.dump(scores_data, f, indent=2)

    _print_report(summary)
    logger.info("Validation results saved to %s", out)
    return summary


# ─── Plot generation ──────────────────────────────────────────


def generate_roc_plot(
    roc_docking: dict,
    roc_gnn: dict,
    roc_consensus: dict,
) -> go.Figure:
    """Generate interactive ROC curve plot with all three methods.

    Args:
        roc_docking: ROC result dict for docking scores.
        roc_gnn: ROC result dict for GNN scores.
        roc_consensus: ROC result dict for consensus scores.

    Returns:
        Plotly Figure with three ROC curves + diagonal baseline.
    """
    fig = go.Figure()

    # Docking only
    fig.add_trace(go.Scatter(
        x=roc_docking["fpr"], y=roc_docking["tpr"],
        mode="lines",
        name=f"Docking Only (AUC = {roc_docking['auc']:.3f})",
        line=dict(color=THEME_PRIMARY, width=2),
    ))

    # ML only
    fig.add_trace(go.Scatter(
        x=roc_gnn["fpr"], y=roc_gnn["tpr"],
        mode="lines",
        name=f"ML Only (AUC = {roc_gnn['auc']:.3f})",
        line=dict(color=THEME_SECONDARY, width=2),
    ))

    # Consensus
    fig.add_trace(go.Scatter(
        x=roc_consensus["fpr"], y=roc_consensus["tpr"],
        mode="lines",
        name=f"Consensus (AUC = {roc_consensus['auc']:.3f})",
        line=dict(color=THEME_ACCENT, width=3),
    ))

    # Random baseline
    fig.add_trace(go.Scatter(
        x=[0, 1], y=[0, 1],
        mode="lines",
        name="Random (AUC = 0.500)",
        line=dict(color="#AAA", width=1, dash="dash"),
    ))

    fig.update_layout(
        title="ROC Curves — Screening Validation",
        xaxis_title="False Positive Rate",
        yaxis_title="True Positive Rate",
        height=500,
        margin=dict(l=10, r=10, t=80, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        xaxis=dict(range=[0, 1]),
        yaxis=dict(range=[0, 1.05]),
    )
    return fig


def generate_enrichment_plot(
    ef_docking: dict,
    ef_gnn: dict,
    ef_consensus: dict,
) -> go.Figure:
    """Generate enrichment factor bar chart comparing methods."""
    categories = ["EF @ 1%", "EF @ 5%", "EF @ 10%"]
    docking_vals = [ef_docking["ef_1pct"], ef_docking["ef_5pct"], ef_docking["ef_10pct"]]
    gnn_vals = [ef_gnn["ef_1pct"], ef_gnn["ef_5pct"], ef_gnn["ef_10pct"]]
    consensus_vals = [ef_consensus["ef_1pct"], ef_consensus["ef_5pct"], ef_consensus["ef_10pct"]]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=categories, y=docking_vals,
        name="Docking Only", marker_color=THEME_PRIMARY,
        text=[f"{v:.1f}" for v in docking_vals], textposition="outside",
    ))
    fig.add_trace(go.Bar(
        x=categories, y=gnn_vals,
        name="ML Only", marker_color=THEME_SECONDARY,
        text=[f"{v:.1f}" for v in gnn_vals], textposition="outside",
    ))
    fig.add_trace(go.Bar(
        x=categories, y=consensus_vals,
        name="Consensus", marker_color=THEME_ACCENT,
        text=[f"{v:.1f}" for v in consensus_vals], textposition="outside",
    ))

    # Reference line at EF = 1.0 (random)
    fig.add_hline(y=1.0, line_dash="dash", line_color="#AAA",
                  annotation_text="Random (EF=1.0)")

    fig.update_layout(
        title="Enrichment Factors by Scoring Method",
        yaxis_title="Enrichment Factor",
        barmode="group",
        height=400,
        margin=dict(l=10, r=10, t=80, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    return fig


def generate_score_distribution_plot(scores_data: dict) -> go.Figure:
    """Generate violin/box plot comparing active vs decoy score distributions."""
    actives = scores_data["actives"]
    decoys = scores_data["decoys"]

    fig = go.Figure()

    methods = [
        ("docking_score", "Docking Score", True),
        ("gnn_score", "ML Score", False),
        ("consensus_score", "Consensus Score", False),
    ]

    for method_key, method_name, negate in methods:
        active_scores = [a[method_key] for a in actives]
        decoy_scores = [d[method_key] for d in decoys]

        # For docking scores, negate so higher = better (consistent display)
        if negate:
            active_scores = [-s for s in active_scores]
            decoy_scores = [-s for s in decoy_scores]
            display_name = f"|{method_name}|"
        else:
            display_name = method_name

        fig.add_trace(go.Box(
            y=active_scores,
            name=f"{display_name}<br>Actives",
            marker_color=THEME_ACCENT,
            boxmean=True,
        ))
        fig.add_trace(go.Box(
            y=decoy_scores,
            name=f"{display_name}<br>Decoys",
            marker_color=THEME_DANGER,
            boxmean=True,
        ))

    fig.update_layout(
        title="Score Distributions — Actives vs Decoys",
        yaxis_title="Score (higher = better)",
        height=450,
        margin=dict(l=10, r=10, t=80, b=10),
        showlegend=False,
    )
    return fig


# ─── Full validation pipeline ─────────────────────────────────


def run_full_validation(
    use_mock: bool = False,
    seed: int = 42,
    output_dir: Optional[Path] = None,
    exhaustiveness: int = 8,
) -> dict:
    """Run the complete validation pipeline and save results.

    By default performs real Vina docking and ML rescoring against
    DENV NS5 RdRp (PDB 5CCV).  Set ``use_mock=True`` to fall back
    to synthetic score generation for offline / rapid testing.

    Args:
        use_mock: If True, use mock score generation instead of real
            docking.  Default False.
        seed: Random seed for mock score reproducibility (ignored when
            use_mock is False).
        output_dir: Directory for results. Defaults to ROC_RESULTS_DIR.
        exhaustiveness: Vina exhaustiveness (only used when
            use_mock is False).

    Returns:
        Summary dict with results for each method.
    """
    if not use_mock:
        return run_real_validation(
            output_dir=output_dir,
            exhaustiveness=exhaustiveness,
        )

    # ── Mock path (retained for offline / rapid testing) ─────
    out = output_dir or ROC_RESULTS_DIR
    out.mkdir(parents=True, exist_ok=True)

    # Generate scores
    scores_data = generate_mock_validation_scores(seed=seed)
    all_entries = scores_data["actives"] + scores_data["decoys"]

    labels = [1 if e["is_active"] else 0 for e in all_entries]

    # For docking: more negative = better, so negate for ROC (higher = better)
    docking_scores = [-e["docking_score"] for e in all_entries]
    gnn_scores = [e["gnn_score"] for e in all_entries]
    consensus_scores = [e["consensus_score"] for e in all_entries]

    # Compute ROC and enrichment for each method
    summary = {}
    for method_name, scores in [
        ("docking", docking_scores),
        ("gnn", gnn_scores),
        ("consensus", consensus_scores),
    ]:
        roc = compute_roc(labels, scores)
        ef = compute_enrichment_factors(labels, scores)
        summary[method_name] = {
            "auc": roc["auc"],
            "fpr": roc["fpr"],
            "tpr": roc["tpr"],
            **ef,
        }

    # Add metadata
    summary["metadata"] = {
        "n_actives": sum(labels),
        "n_decoys": len(labels) - sum(labels),
        "n_total": len(labels),
        "seed": seed,
        "target_pdb": "5CCV",
        "target_name": "DENV NS5 RdRp",
        "scoring": "mock",
    }

    # Interpret results
    consensus_auc = summary["consensus"]["auc"]
    if consensus_auc > 0.85:
        summary["verdict"] = "EXCELLENT"
    elif consensus_auc >= 0.70:
        summary["verdict"] = "GOOD"
    elif consensus_auc >= 0.60:
        summary["verdict"] = "ACCEPTABLE"
    else:
        summary["verdict"] = "POOR"

    # Save CSV files
    _save_scores_csv(all_entries, "docking_score", out / "docking_scores.csv")
    _save_scores_csv(all_entries, "gnn_score", out / "gnn_scores.csv")
    _save_scores_csv(all_entries, "consensus_score", out / "consensus_scores.csv")

    # Save summary JSON (without large FPR/TPR arrays for cleanliness)
    summary_compact = {}
    for key in ["docking", "gnn", "consensus"]:
        summary_compact[key] = {
            "auc": summary[key]["auc"],
            "ef_1pct": summary[key]["ef_1pct"],
            "ef_5pct": summary[key]["ef_5pct"],
            "ef_10pct": summary[key]["ef_10pct"],
        }
    summary_compact["metadata"] = summary["metadata"]
    summary_compact["verdict"] = summary["verdict"]

    summary_path = out / "validation_summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary_compact, f, indent=2)

    # Save raw scores for dashboard loading
    scores_path = out / "validation_scores.json"
    with open(scores_path, "w") as f:
        json.dump(scores_data, f, indent=2)

    # Print report
    _print_report(summary)

    logger.info("Validation results saved to %s", out)
    return summary


def load_validation_results(
    results_dir: Optional[Path] = None,
) -> Optional[dict]:
    """Load previously saved validation results.

    Args:
        results_dir: Directory containing results. Defaults to ROC_RESULTS_DIR.

    Returns:
        Summary dict if results exist, None otherwise.
    """
    d = results_dir or ROC_RESULTS_DIR
    summary_path = d / "validation_summary.json"
    scores_path = d / "validation_scores.json"

    if not summary_path.exists():
        return None

    with open(summary_path) as f:
        summary = json.load(f)

    if scores_path.exists():
        with open(scores_path) as f:
            summary["_scores_data"] = json.load(f)

    return summary


def _save_scores_csv(entries: list[dict], score_key: str, path: Path) -> None:
    """Save scores to a CSV with name, label, and score columns."""
    rows = []
    for e in entries:
        rows.append({
            "name": e["name"],
            "is_active": e.get("is_active", False),
            "score": e[score_key],
        })
    pd.DataFrame(rows).to_csv(path, index=False)


def _print_report(summary: dict) -> None:
    """Print a formatted validation report to stdout."""
    print("\n" + "=" * 50)
    print("  VALIDATION RESULTS")
    print("=" * 50)
    print(f"  Target: {summary['metadata']['target_name']} ({summary['metadata']['target_pdb']})")
    print(f"  Actives: {summary['metadata']['n_actives']}")
    print(f"  Decoys:  {summary['metadata']['n_decoys']}")
    print(f"  Total:   {summary['metadata']['n_total']}")
    scoring = summary["metadata"].get("scoring", "unknown")
    print(f"  Scoring: {scoring}")
    print()
    print(f"  {'Method':<16} {'AUC-ROC':>8} {'EF@1%':>8} {'EF@5%':>8} {'EF@10%':>8}")
    print("  " + "-" * 48)
    for method in ["docking", "gnn", "consensus"]:
        m = summary[method]
        name = {"docking": "Docking only", "gnn": "ML only", "consensus": "Consensus"}[method]
        print(f"  {name:<16} {m['auc']:>8.3f} {m['ef_1pct']:>8.1f} {m['ef_5pct']:>8.1f} {m['ef_10pct']:>8.1f}")
    print(f"  {'Random':<16} {'0.500':>8} {'1.0':>8} {'1.0':>8} {'1.0':>8}")
    print()
    print(f"  Verdict: {summary['verdict']}")
    print("=" * 50 + "\n")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_full_validation()
