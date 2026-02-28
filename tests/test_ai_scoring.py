"""Tests for AI scoring and ADMET prediction."""

import pytest

from src.ai_scoring.admet_predict import (
    full_admet_profile,
    predict_bioavailability,
    predict_herg,
    predict_lipinski,
    predict_toxicity,
)
from src.ai_scoring.ml_rescore import (
    _smiles_to_features,
    consensus_score,
    load_model,
    rescore_single,
)
from src.ai_scoring.literature_mining import (
    extract_relationships,
    search_pubmed,
)
from src.ai_scoring.consensus_rank import (
    compute_consensus,
    flag_novel_discoveries,
    get_top_candidates,
)
from src.utils.db import get_connection, init_db


# ─── Known drug SMILES for testing ───────────────────────

ASPIRIN_SMILES = "CC(=O)Oc1ccccc1C(=O)O"
IBUPROFEN_SMILES = "CC(C)Cc1ccc(cc1)C(C)C(=O)O"
CAFFEINE_SMILES = "Cn1c(=O)c2c(ncn2C)n(C)c1=O"
METFORMIN_SMILES = "CN(C)C(=N)NC(=N)N"
INVALID_SMILES = "NOT_A_VALID_SMILES_STRING"


# ─── Lipinski tests ──────────────────────────────────────


class TestLipinski:
    def test_aspirin_passes(self):
        result = predict_lipinski(ASPIRIN_SMILES)
        assert result["pass"] is True
        assert result["violations"] == 0
        assert 170 < result["mw"] < 190  # MW ~180

    def test_ibuprofen_passes(self):
        result = predict_lipinski(IBUPROFEN_SMILES)
        assert result["pass"] is True

    def test_caffeine_passes(self):
        result = predict_lipinski(CAFFEINE_SMILES)
        assert result["pass"] is True

    def test_metformin_passes(self):
        result = predict_lipinski(METFORMIN_SMILES)
        assert result["pass"] is True
        assert result["mw"] < 500

    def test_invalid_smiles_fails(self):
        result = predict_lipinski(INVALID_SMILES)
        assert result["pass"] is False
        assert result["violations"] == 4

    def test_result_keys(self):
        result = predict_lipinski(ASPIRIN_SMILES)
        assert "mw" in result
        assert "logp" in result
        assert "hbd" in result
        assert "hba" in result
        assert "pass" in result
        assert "violations" in result


# ─── ADMET prediction tests ──────────────────────────────


class TestADMET:
    def test_toxicity_returns_float(self):
        risk = predict_toxicity(ASPIRIN_SMILES)
        assert isinstance(risk, float)
        assert 0.0 <= risk <= 1.0

    def test_herg_returns_float(self):
        risk = predict_herg(ASPIRIN_SMILES)
        assert isinstance(risk, float)
        assert 0.0 <= risk <= 1.0

    def test_bioavailability_returns_float(self):
        bio = predict_bioavailability(ASPIRIN_SMILES)
        assert isinstance(bio, float)
        assert 0.0 <= bio <= 1.0

    def test_aspirin_bioavailability_good(self):
        bio = predict_bioavailability(ASPIRIN_SMILES)
        assert bio >= 0.5  # Aspirin has good oral bioavailability

    def test_full_profile_keys(self):
        profile = full_admet_profile(ASPIRIN_SMILES)
        assert "lipinski_pass" in profile
        assert "hepatotoxicity_risk" in profile
        assert "herg_inhibition_risk" in profile
        assert "oral_bioavailability" in profile
        assert "overall_pass" in profile

    def test_full_profile_aspirin(self):
        profile = full_admet_profile(ASPIRIN_SMILES)
        assert profile["lipinski_pass"] is True

    def test_invalid_smiles_toxicity(self):
        assert predict_toxicity(INVALID_SMILES) == 1.0

    def test_invalid_smiles_herg(self):
        assert predict_herg(INVALID_SMILES) == 1.0

    def test_invalid_smiles_bioavailability(self):
        assert predict_bioavailability(INVALID_SMILES) == 0.0


# ─── Consensus scoring tests ─────────────────────────────


class TestConsensusScore:
    def test_basic_calculation(self):
        score = consensus_score(-10.0, 0.8)
        assert 0.0 <= score <= 1.0

    def test_perfect_scores(self):
        # Best Vina (-12.0) -> norm 1.0, best ML (1.0)
        score = consensus_score(-12.0, 1.0)
        assert score == 1.0

    def test_worst_scores(self):
        # Worst Vina (-4.0) -> norm 0.0, worst ML (0.0)
        score = consensus_score(-4.0, 0.0)
        assert score == 0.0

    def test_custom_weights(self):
        # Use asymmetric scores so weights produce different results
        score_default = consensus_score(-10.0, 0.3)
        score_vina_heavy = consensus_score(-10.0, 0.3, weights=(0.7, 0.3))
        assert score_default != score_vina_heavy

    def test_score_range(self):
        for vina in [-12.0, -10.0, -8.0, -6.0, -4.0]:
            for ml in [0.0, 0.25, 0.5, 0.75, 1.0]:
                score = consensus_score(vina, ml)
                assert 0.0 <= score <= 1.0, f"Out of range: vina={vina}, ml={ml}"


# ─── ML rescoring tests ──────────────────────────────────


class TestMLRescore:
    def test_load_model(self):
        model, backend = load_model()
        assert model is not None
        assert backend == "sklearn"

    def test_smiles_to_features(self):
        features = _smiles_to_features(ASPIRIN_SMILES, vina_score=-7.0)
        assert features is not None
        assert len(features) == 2049  # 2048-bit Morgan FP + 1 Vina norm

    def test_smiles_to_features_target_specific(self):
        """Same drug with different Vina scores should produce different features."""
        f1 = _smiles_to_features(ASPIRIN_SMILES, vina_score=-7.0)
        f2 = _smiles_to_features(ASPIRIN_SMILES, vina_score=-10.0)
        assert f1 is not None and f2 is not None
        assert f1[-1] != f2[-1]  # Vina norm differs

    def test_smiles_to_features_invalid(self):
        assert _smiles_to_features(INVALID_SMILES) is None

    def test_rescore_single(self):
        score = rescore_single(ASPIRIN_SMILES, "DENV_NS3", -8.0)
        assert score is not None
        assert 0.0 <= score <= 1.0

    def test_rescore_different_drugs(self):
        s1 = rescore_single(ASPIRIN_SMILES, "DENV_NS3", -8.0)
        s2 = rescore_single(CAFFEINE_SMILES, "DENV_NS3", -8.0)
        assert s1 is not None
        assert s2 is not None


# ─── Relationship extraction tests ────────────────────────


class TestRelationshipExtraction:
    def test_therapeutic_keywords(self):
        text = (
            "The compound showed potent antiviral activity against dengue virus "
            "and effectively inhibited NS3 protease function in cell-based assays."
        )
        rels = extract_relationships(text)
        types = [r["relationship"] for r in rels]
        assert "therapeutic" in types

    def test_mechanistic_keywords(self):
        text = (
            "Molecular docking studies revealed strong binding affinity between "
            "the drug and the receptor active site through multiple interactions."
        )
        rels = extract_relationships(text)
        types = [r["relationship"] for r in rels]
        assert "mechanistic" in types

    def test_adverse_keywords(self):
        text = (
            "The drug exhibited significant hepatotoxicity and adverse "
            "cardiac effects at therapeutic doses."
        )
        rels = extract_relationships(text)
        types = [r["relationship"] for r in rels]
        assert "adverse" in types

    def test_pharmacokinetic_keywords(self):
        text = (
            "The oral bioavailability was measured at 85% with rapid absorption "
            "and a plasma half-life of 6 hours."
        )
        rels = extract_relationships(text)
        types = [r["relationship"] for r in rels]
        assert "pharmacokinetic" in types

    def test_empty_text(self):
        assert extract_relationships("") == []

    def test_confidence_range(self):
        text = "The drug inhibits viral replication and shows antiviral therapeutic potential."
        rels = extract_relationships(text)
        for rel in rels:
            assert 0.0 <= rel["confidence"] <= 1.0


# ─── PubMed search test ──────────────────────────────────


class TestPubMedSearch:
    @pytest.mark.network
    def test_basic_search(self):
        results = search_pubmed("dengue NS3 protease inhibitor", max_results=3)
        assert isinstance(results, list)
        if results:
            assert "pmid" in results[0]
            assert "title" in results[0]


# ─── Database integration tests ──────────────────────────


class TestDatabaseIntegration:
    def test_compute_consensus_empty(self, tmp_path):
        db_path = tmp_path / "test.db"
        init_db(db_path)

        df = compute_consensus("DENV_NS3", db_path=db_path)
        assert df.empty

    def test_get_top_candidates_empty(self, tmp_path):
        db_path = tmp_path / "test.db"
        init_db(db_path)

        df = get_top_candidates("DENV_NS3", db_path=db_path)
        assert df.empty

    def test_flag_novel_empty(self, tmp_path):
        db_path = tmp_path / "test.db"
        init_db(db_path)

        df = flag_novel_discoveries("DENV_NS3", db_path=db_path)
        assert df.empty
