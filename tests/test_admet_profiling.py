"""Tests for Phase 15 full ADMET profiling."""

import pytest

from src.admet.descriptors import (
    compute_descriptors,
    check_lipinski,
    check_veber,
    check_ghose,
    check_egan,
    check_pains,
    check_brenk,
    estimate_esol,
)


# Known molecule SMILES
ASPIRIN = "CC(=O)Oc1ccccc1C(=O)O"
CAFFEINE = "Cn1c(=O)c2c(ncn2C)n(C)c1=O"
IBUPROFEN = "CC(C)Cc1ccc(cc1)C(C)C(=O)O"
CYCLOSPORINE = "CC1C(=O)NC(C(=O)NC(C(=O)NC(C(=O)NC(C(=O)NC(C(=O)NC(C(=O)NC(C(=O)NC(C(=O)NC(C(=O)NC(C(=O)NC1=O)C(C)C)CC(C)C)CC(C)C)C)CC(C)C)C(C)C)CC(C)C)C)CC(C)C)C(C)C"
DIAZEPAM = "ClC1=CC2=C(C=C1)N(C)C(=O)CN=C2C1=CC=CC=C1"
INVALID_SMILES = "NOT_A_MOLECULE"


class TestComputeDescriptors:
    def test_aspirin_mw(self):
        d = compute_descriptors(ASPIRIN)
        assert 179 < d["mw"] < 181

    def test_aspirin_logp(self):
        d = compute_descriptors(ASPIRIN)
        assert 0.5 < d["logp"] < 2.0

    def test_aspirin_tpsa(self):
        d = compute_descriptors(ASPIRIN)
        assert 60 < d["tpsa"] < 70

    def test_aspirin_hbd(self):
        d = compute_descriptors(ASPIRIN)
        assert d["hbd"] == 1

    def test_aspirin_hba(self):
        d = compute_descriptors(ASPIRIN)
        assert d["hba"] == 3

    def test_aspirin_rotatable_bonds(self):
        d = compute_descriptors(ASPIRIN)
        assert d["rotatable_bonds"] == 2

    def test_aspirin_aromatic_rings(self):
        d = compute_descriptors(ASPIRIN)
        assert d["aromatic_rings"] == 1

    def test_aspirin_heavy_atoms(self):
        d = compute_descriptors(ASPIRIN)
        assert d["heavy_atoms"] == 13

    def test_aspirin_fraction_csp3(self):
        d = compute_descriptors(ASPIRIN)
        assert 0.0 < d["fraction_csp3"] < 0.3

    def test_aspirin_mol_refractivity(self):
        d = compute_descriptors(ASPIRIN)
        assert 40 < d["mol_refractivity"] < 50

    def test_returns_all_keys(self):
        d = compute_descriptors(ASPIRIN)
        required = {
            "mw", "logp", "tpsa", "hbd", "hba", "rotatable_bonds",
            "aromatic_rings", "heavy_atoms", "fraction_csp3",
            "mol_refractivity",
        }
        assert required.issubset(d.keys())

    def test_invalid_smiles_returns_none(self):
        d = compute_descriptors(INVALID_SMILES)
        assert d is None

    def test_caffeine_descriptors(self):
        d = compute_descriptors(CAFFEINE)
        assert 193 < d["mw"] < 195
        assert d["hbd"] == 0
        assert d["aromatic_rings"] == 2


class TestLipinskiFilter:
    def test_aspirin_passes(self):
        d = compute_descriptors(ASPIRIN)
        result = check_lipinski(d)
        assert result["pass"] is True
        assert result["violations"] == 0

    def test_cyclosporine_fails(self):
        d = compute_descriptors(CYCLOSPORINE)
        result = check_lipinski(d)
        assert result["pass"] is False
        assert result["violations"] >= 2


class TestVeberFilter:
    def test_aspirin_passes(self):
        d = compute_descriptors(ASPIRIN)
        result = check_veber(d)
        assert result["pass"] is True

    def test_returns_criteria(self):
        d = compute_descriptors(ASPIRIN)
        result = check_veber(d)
        assert "tpsa_ok" in result
        assert "rotbonds_ok" in result


class TestGhoseFilter:
    def test_diazepam_passes(self):
        d = compute_descriptors(DIAZEPAM)
        result = check_ghose(d)
        assert result["pass"] is True

    def test_returns_criteria(self):
        d = compute_descriptors(DIAZEPAM)
        result = check_ghose(d)
        assert "mw_ok" in result
        assert "logp_ok" in result
        assert "atoms_ok" in result
        assert "mr_ok" in result


class TestEganFilter:
    def test_aspirin_passes(self):
        d = compute_descriptors(ASPIRIN)
        result = check_egan(d)
        assert result["pass"] is True

    def test_returns_criteria(self):
        d = compute_descriptors(ASPIRIN)
        result = check_egan(d)
        assert "tpsa_ok" in result
        assert "logp_ok" in result


class TestESOL:
    def test_aspirin_soluble(self):
        d = compute_descriptors(ASPIRIN)
        log_s = estimate_esol(d)
        assert -4.0 < log_s < 0.0

    def test_returns_float(self):
        d = compute_descriptors(CAFFEINE)
        log_s = estimate_esol(d)
        assert isinstance(log_s, float)


class TestPAINS:
    def test_aspirin_no_pains(self):
        alerts = check_pains(ASPIRIN)
        assert len(alerts) == 0

    def test_returns_list(self):
        alerts = check_pains(IBUPROFEN)
        assert isinstance(alerts, list)

    def test_invalid_smiles_empty(self):
        alerts = check_pains(INVALID_SMILES)
        assert alerts == []

    def test_known_pains_detected(self):
        rhodanine = "O=C1CSC(=S)N1"
        alerts = check_pains(rhodanine)
        assert len(alerts) > 0


class TestBrenk:
    def test_aspirin_no_brenk(self):
        alerts = check_brenk(ASPIRIN)
        assert isinstance(alerts, list)

    def test_invalid_smiles_empty(self):
        alerts = check_brenk(INVALID_SMILES)
        assert alerts == []
