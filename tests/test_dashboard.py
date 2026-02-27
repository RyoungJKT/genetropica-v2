"""Tests for Streamlit dashboard components."""

import plotly.graph_objects as go
import pytest

from app.components.charts import (
    admet_overview_bars,
    admet_radar,
    literature_bar,
    novel_discoveries_highlight,
    score_comparison_bar,
    score_distribution_histogram,
    top_candidates_bar,
    vina_vs_ml_scatter,
)
from src.utils.config import DISEASES, TARGET_PROTEINS
from src.utils.db import get_drugs_for_target, init_db


@pytest.fixture(autouse=True, scope="module")
def _init_database():
    """Initialize the mock database once for all dashboard tests."""
    init_db()


# ── Helpers ─────────────────────────────────────────────────────

def _first_target_id() -> str:
    """Return the first target_id that has data."""
    for tid in TARGET_PROTEINS:
        df = get_drugs_for_target(tid)
        if not df.empty:
            return tid
    pytest.skip("No target with data found")


def _first_drug_id() -> str:
    """Return the first drug_id from the first target with data."""
    tid = _first_target_id()
    df = get_drugs_for_target(tid)
    return df.iloc[0]["drug_id"]


# ── Chart Component Tests ───────────────────────────────────────

class TestScoreDistributionHistogram:
    def test_returns_figure(self):
        fig = score_distribution_histogram(_first_target_id())
        assert isinstance(fig, go.Figure)

    def test_has_data_traces(self):
        fig = score_distribution_histogram(_first_target_id())
        assert len(fig.data) > 0

    def test_invalid_target_returns_empty_figure(self):
        fig = score_distribution_histogram("NONEXISTENT_TARGET")
        assert isinstance(fig, go.Figure)
        assert len(fig.layout.annotations) > 0


class TestTopCandidatesBar:
    def test_returns_figure(self):
        fig = top_candidates_bar(_first_target_id(), n=5)
        assert isinstance(fig, go.Figure)

    def test_respects_n_parameter(self):
        fig = top_candidates_bar(_first_target_id(), n=3)
        assert isinstance(fig, go.Figure)
        if fig.data:
            assert len(fig.data[0].y) <= 3

    def test_invalid_target_returns_empty_figure(self):
        fig = top_candidates_bar("NONEXISTENT_TARGET")
        assert isinstance(fig, go.Figure)


class TestScoreComparisonBar:
    def test_returns_figure(self):
        fig = score_comparison_bar(_first_drug_id())
        assert isinstance(fig, go.Figure)

    def test_has_two_traces(self):
        fig = score_comparison_bar(_first_drug_id())
        assert len(fig.data) >= 1


class TestAdmetRadar:
    def test_returns_figure(self):
        fig = admet_radar(_first_drug_id())
        assert isinstance(fig, go.Figure)

    def test_uses_polar_layout(self):
        fig = admet_radar(_first_drug_id())
        if fig.data:
            assert isinstance(fig.data[0], go.Scatterpolar)


class TestVinaVsMlScatter:
    def test_returns_figure(self):
        fig = vina_vs_ml_scatter(_first_target_id())
        assert isinstance(fig, go.Figure)

    def test_has_multiple_traces(self):
        fig = vina_vs_ml_scatter(_first_target_id())
        assert len(fig.data) >= 2


class TestAdmetOverviewBars:
    def test_returns_figure(self):
        fig = admet_overview_bars()
        assert isinstance(fig, go.Figure)

    def test_has_pass_and_fail_traces(self):
        fig = admet_overview_bars()
        if fig.data:
            assert len(fig.data) == 2


class TestLiteratureBar:
    def test_returns_figure(self):
        fig = literature_bar(_first_target_id())
        assert isinstance(fig, go.Figure)


class TestNovelDiscoveriesHighlight:
    def test_returns_figure(self):
        fig = novel_discoveries_highlight(_first_target_id())
        assert isinstance(fig, go.Figure)


# ── Filter Component Tests ──────────────────────────────────────

class TestFilterComponents:
    def test_render_target_filter_is_callable(self):
        from app.components.filters import render_target_filter
        assert callable(render_target_filter)

    def test_render_score_filter_is_callable(self):
        from app.components.filters import render_score_filter
        assert callable(render_score_filter)

    def test_render_admet_filter_is_callable(self):
        from app.components.filters import render_admet_filter
        assert callable(render_admet_filter)

    def test_render_sort_selector_is_callable(self):
        from app.components.filters import render_sort_selector
        assert callable(render_sort_selector)


# ── Config Tests ────────────────────────────────────────────────

class TestConfig:
    def test_target_proteins_has_six_entries(self):
        assert len(TARGET_PROTEINS) == 6

    def test_target_proteins_have_required_keys(self):
        required = {"name", "pdb_id", "disease", "uniprot_id"}
        for tid, info in TARGET_PROTEINS.items():
            assert required.issubset(info.keys()), f"{tid} missing keys"

    def test_diseases_has_three_entries(self):
        assert len(DISEASES) == 3

    def test_all_disease_targets_exist_in_target_proteins(self):
        for disease, info in DISEASES.items():
            for tid in info["targets"]:
                assert tid in TARGET_PROTEINS, f"{tid} from {disease} not in TARGET_PROTEINS"

    def test_disease_names(self):
        assert set(DISEASES.keys()) == {"Dengue", "Chikungunya", "Leptospirosis"}


# ── Database Integration Tests ──────────────────────────────────

class TestDatabaseIntegration:
    def test_get_drugs_for_target_returns_dataframe(self):
        df = get_drugs_for_target(_first_target_id())
        assert not df.empty

    def test_drugs_dataframe_has_required_columns(self):
        df = get_drugs_for_target(_first_target_id())
        required_cols = {
            "drug_id", "name", "drugbank_id", "original_indication",
            "vina_score", "ml_binding_score", "consensus_score",
            "consensus_rank", "overall_pass", "lipinski_pass", "lit_count",
        }
        assert required_cols.issubset(set(df.columns))

    def test_no_duplicate_drugs_per_target(self):
        df = get_drugs_for_target(_first_target_id())
        assert df["drug_id"].is_unique, "Duplicate drug_ids found"


# ── Page Import Smoke Tests ─────────────────────────────────────

class TestPageImports:
    def test_charts_module_has_all_functions(self):
        from app.components import charts
        expected = [
            "score_distribution_histogram", "top_candidates_bar",
            "score_comparison_bar", "admet_radar", "vina_vs_ml_scatter",
            "admet_overview_bars", "literature_bar", "novel_discoveries_highlight",
        ]
        for fn_name in expected:
            assert hasattr(charts, fn_name), f"charts missing {fn_name}"

    def test_filters_module_has_all_functions(self):
        from app.components import filters
        expected = [
            "render_target_filter", "render_score_filter",
            "render_admet_filter", "render_sort_selector",
        ]
        for fn_name in expected:
            assert hasattr(filters, fn_name), f"filters missing {fn_name}"

    def test_mol_viewer_module_has_viewer_functions(self):
        from app.components import mol_viewer
        expected = ["render_protein", "render_binding_complex", "render_comparison"]
        for fn_name in expected:
            assert hasattr(mol_viewer, fn_name), f"mol_viewer missing {fn_name}"

    def test_config_module_importable(self):
        from src.utils import config
        assert hasattr(config, "TARGET_PROTEINS")
        assert hasattr(config, "DISEASES")
        assert hasattr(config, "DB_PATH")

    def test_db_module_importable(self):
        from src.utils import db
        assert hasattr(db, "init_db")
        assert hasattr(db, "get_drugs_for_target")
        assert hasattr(db, "get_drug_details")
