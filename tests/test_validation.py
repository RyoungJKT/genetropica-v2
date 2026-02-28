"""Tests for Phase 12 virtual screening validation."""

import numpy as np
import pytest

from src.validation.collect_actives import KNOWN_ACTIVES, build_actives_manifest


# ─── Known actives tests ────────────────────────────────────


class TestKnownActives:
    def test_eight_actives_defined(self):
        assert len(KNOWN_ACTIVES) == 8

    def test_sofosbuvir_present(self):
        names = [a["name"] for a in KNOWN_ACTIVES]
        assert "Sofosbuvir" in names

    def test_ribavirin_present(self):
        names = [a["name"] for a in KNOWN_ACTIVES]
        assert "Ribavirin" in names

    def test_all_have_required_fields(self):
        required = {"name", "pubchem_cid", "activity", "smiles", "source_paper"}
        for active in KNOWN_ACTIVES:
            assert required.issubset(active.keys()), f"Missing fields in {active.get('name')}"

    def test_all_smiles_parseable(self):
        from rdkit import Chem

        for active in KNOWN_ACTIVES:
            mol = Chem.MolFromSmiles(active["smiles"])
            assert mol is not None, f"Invalid SMILES for {active['name']}"

    def test_build_manifest(self):
        df = build_actives_manifest()
        assert len(df) == 8
        assert "name" in df.columns
        assert "pubchem_cid" in df.columns
        assert "smiles" in df.columns
        assert "activity" in df.columns

    def test_pubchem_cids_unique(self):
        cids = [a["pubchem_cid"] for a in KNOWN_ACTIVES]
        assert len(cids) == len(set(cids))


# ─── Decoy generation tests ─────────────────────────────────


from src.validation.generate_decoys import generate_decoys_for_active, generate_all_decoys


class TestDecoyGeneration:
    def test_generates_decoys(self):
        """Generate decoys for ribavirin (small nucleoside)."""
        smiles = "OC[C@@H]1OC(N2N=CN=C2C(N)=O)[C@@H](O)[C@H]1O"
        decoys = generate_decoys_for_active(smiles, n_decoys=10, seed=42)
        assert len(decoys) >= 1
        assert len(decoys) <= 10

    def test_decoys_are_valid_smiles(self):
        """All returned decoys should be parseable by RDKit."""
        from rdkit import Chem

        smiles = "OC[C@@H]1OC(N2N=CN=C2C(N)=O)[C@@H](O)[C@H]1O"
        decoys = generate_decoys_for_active(smiles, n_decoys=10, seed=42)
        for smi in decoys:
            mol = Chem.MolFromSmiles(smi)
            assert mol is not None, f"Invalid decoy SMILES: {smi}"

    def test_decoys_topologically_dissimilar(self):
        """Decoys should have Tanimoto < 0.5 vs active."""
        from rdkit import Chem
        from rdkit.Chem import AllChem, DataStructs

        active_smiles = "OC[C@@H]1OC(N2N=CN=C2C(N)=O)[C@@H](O)[C@H]1O"
        decoys = generate_decoys_for_active(active_smiles, n_decoys=10, seed=42)

        active_mol = Chem.MolFromSmiles(active_smiles)
        active_fp = AllChem.GetMorganFingerprintAsBitVect(active_mol, 2, nBits=2048)

        for d_smi in decoys:
            d_mol = Chem.MolFromSmiles(d_smi)
            d_fp = AllChem.GetMorganFingerprintAsBitVect(d_mol, 2, nBits=2048)
            sim = DataStructs.TanimotoSimilarity(active_fp, d_fp)
            assert sim < 0.5, f"Decoy {d_smi} too similar: Tanimoto={sim:.3f}"

    def test_decoys_property_matched(self):
        """Decoys should have MW within 35% and LogP within 2.0."""
        from rdkit import Chem
        from rdkit.Chem import Descriptors

        active_smiles = "OC[C@@H]1OC(N2N=CN=C2C(N)=O)[C@@H](O)[C@H]1O"
        active_mol = Chem.MolFromSmiles(active_smiles)
        active_mw = Descriptors.MolWt(active_mol)
        active_logp = Descriptors.MolLogP(active_mol)

        decoys = generate_decoys_for_active(active_smiles, n_decoys=10, seed=42)
        for d_smi in decoys:
            d_mol = Chem.MolFromSmiles(d_smi)
            d_mw = Descriptors.MolWt(d_mol)
            d_logp = Descriptors.MolLogP(d_mol)
            assert abs(d_mw - active_mw) / active_mw < 0.35, (
                f"MW mismatch: active={active_mw:.0f}, decoy={d_mw:.0f}"
            )
            assert abs(d_logp - active_logp) < 2.0, (
                f"LogP mismatch: active={active_logp:.1f}, decoy={d_logp:.1f}"
            )

    def test_generate_all_decoys(self):
        """Full decoy set should have entries from multiple actives."""
        result = generate_all_decoys(n_per_active=5, seed=42)
        assert len(result) >= 5  # at least some decoys
        assert "smiles" in result.columns
        assert "source_active" in result.columns
        assert "is_decoy" in result.columns
        # Should have decoys from more than one active
        assert result["source_active"].nunique() >= 1

    def test_invalid_smiles_returns_empty(self):
        """Invalid SMILES should return empty list, not crash."""
        decoys = generate_decoys_for_active("NOT_VALID", n_decoys=5, seed=42)
        assert decoys == []


# ─── ROC validation tests ────────────────────────────────────


from src.validation.roc_validation import (
    compute_roc,
    compute_enrichment_factors,
    generate_mock_validation_scores,
    run_full_validation,
    generate_roc_plot,
    generate_enrichment_plot,
    generate_score_distribution_plot,
)


class TestROCComputation:
    def test_perfect_separation(self):
        """Perfect separation should give AUC = 1.0."""
        labels = [1, 1, 1, 0, 0, 0]
        scores = [0.9, 0.8, 0.7, 0.3, 0.2, 0.1]
        result = compute_roc(labels, scores)
        assert result["auc"] == pytest.approx(1.0)
        assert len(result["fpr"]) > 2
        assert len(result["tpr"]) > 2

    def test_random_separation(self):
        """Random scores should give AUC ~0.5."""
        np.random.seed(42)
        labels = [1] * 50 + [0] * 200
        scores = list(np.random.uniform(0, 1, 250))
        result = compute_roc(labels, scores)
        assert 0.3 < result["auc"] < 0.7

    def test_roc_returns_required_keys(self):
        labels = [1, 0, 1, 0]
        scores = [0.9, 0.1, 0.8, 0.2]
        result = compute_roc(labels, scores)
        assert "auc" in result
        assert "fpr" in result
        assert "tpr" in result
        assert "thresholds" in result


class TestEnrichmentFactors:
    def test_perfect_enrichment(self):
        """All actives at top => maximum enrichment."""
        labels = [1] * 10 + [0] * 90
        scores = list(range(100, 0, -1))
        ef = compute_enrichment_factors(labels, scores)
        assert ef["ef_10pct"] == pytest.approx(10.0)

    def test_random_enrichment(self):
        """Random ordering => EF ~1.0."""
        np.random.seed(123)
        labels = [1] * 20 + [0] * 180
        scores = list(np.random.uniform(0, 1, 200))
        ef = compute_enrichment_factors(labels, scores)
        # EF at 10% for random should be around 1.0 (+/- noise)
        assert 0.0 <= ef["ef_10pct"] <= 5.0

    def test_enrichment_keys(self):
        labels = [1, 0, 1, 0]
        scores = [0.9, 0.1, 0.8, 0.2]
        ef = compute_enrichment_factors(labels, scores)
        assert "ef_1pct" in ef
        assert "ef_5pct" in ef
        assert "ef_10pct" in ef


class TestMockScores:
    def test_mock_scores_structure(self):
        """Mock scores should contain actives and decoys."""
        result = generate_mock_validation_scores(seed=42)
        assert "actives" in result
        assert "decoys" in result
        assert len(result["actives"]) == 8
        assert len(result["decoys"]) == 200

    def test_mock_actives_have_fields(self):
        result = generate_mock_validation_scores(seed=42)
        for entry in result["actives"]:
            assert "name" in entry
            assert "docking_score" in entry
            assert "gnn_score" in entry
            assert "consensus_score" in entry
            assert entry["is_active"] is True

    def test_mock_decoys_have_fields(self):
        result = generate_mock_validation_scores(seed=42)
        for entry in result["decoys"][:5]:
            assert "docking_score" in entry
            assert "gnn_score" in entry
            assert "consensus_score" in entry
            assert entry["is_active"] is False

    def test_actives_score_better_on_average(self):
        """Actives should have stronger docking scores on average."""
        result = generate_mock_validation_scores(seed=42)
        active_mean = np.mean([a["docking_score"] for a in result["actives"]])
        decoy_mean = np.mean([d["docking_score"] for d in result["decoys"]])
        # Active mean should be more negative (stronger binding)
        assert active_mean < decoy_mean


class TestFullValidation:
    def test_full_validation_returns_summary(self, tmp_path):
        summary = run_full_validation(use_mock=True, seed=42, output_dir=tmp_path)
        assert "docking" in summary
        assert "gnn" in summary
        assert "consensus" in summary
        assert "verdict" in summary

    def test_full_validation_auc_range(self, tmp_path):
        summary = run_full_validation(use_mock=True, seed=42, output_dir=tmp_path)
        for method in ["docking", "gnn", "consensus"]:
            assert 0.5 < summary[method]["auc"] <= 1.0

    def test_consensus_outperforms_random(self, tmp_path):
        summary = run_full_validation(use_mock=True, seed=42, output_dir=tmp_path)
        assert summary["consensus"]["auc"] > 0.6

    def test_saves_output_files(self, tmp_path):
        run_full_validation(use_mock=True, seed=42, output_dir=tmp_path)
        assert (tmp_path / "validation_summary.json").exists()
        assert (tmp_path / "docking_scores.csv").exists()
        assert (tmp_path / "gnn_scores.csv").exists()
        assert (tmp_path / "consensus_scores.csv").exists()
        assert (tmp_path / "validation_scores.json").exists()

    def test_verdict_is_valid(self, tmp_path):
        summary = run_full_validation(use_mock=True, seed=42, output_dir=tmp_path)
        assert summary["verdict"] in ("EXCELLENT", "GOOD", "ACCEPTABLE", "POOR")


class TestPlotGeneration:
    def test_roc_plot_creates_figure(self):
        labels = [1, 1, 0, 0, 0]
        scores = [0.9, 0.8, 0.3, 0.2, 0.1]
        roc = compute_roc(labels, scores)
        fig = generate_roc_plot(roc, roc, roc)
        assert fig is not None
        assert len(fig.data) == 4  # 3 methods + baseline

    def test_enrichment_plot_creates_figure(self):
        labels = [1, 1, 0, 0, 0]
        scores = [0.9, 0.8, 0.3, 0.2, 0.1]
        ef = compute_enrichment_factors(labels, scores)
        fig = generate_enrichment_plot(ef, ef, ef)
        assert fig is not None
        assert len(fig.data) == 3  # 3 method bars

    def test_score_distribution_plot(self):
        data = generate_mock_validation_scores(seed=42)
        fig = generate_score_distribution_plot(data)
        assert fig is not None
        assert len(fig.data) == 6  # 3 methods x 2 (actives/decoys)
