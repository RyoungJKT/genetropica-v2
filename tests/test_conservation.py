"""Tests for Phase 13 evolutionary conservation analysis."""

import numpy as np
import pytest
from unittest.mock import patch, MagicMock

from src.conservation.fetch_sequences import (
    RDRP_SEQUENCES,
    parse_fasta,
    extract_ns5_domain,
    fetch_sequence,
)
from src.conservation.run_alignment import (
    parse_clustal_alignment,
    compute_pairwise_identity,
    compute_per_position_identity,
)
from src.conservation.conservation_scores import (
    compute_shannon_entropy,
    normalize_to_consurf_scale,
    compute_binding_site_test,
    extract_key_residue_conservation,
)
from src.conservation.map_to_structure import (
    write_conservation_pdb,
    generate_pymol_script,
    generate_conservation_viewer_html,
)


# ─── Sequence configuration tests ─────────────────────────────


class TestSequenceConfig:
    def test_nine_viruses_defined(self):
        assert len(RDRP_SEQUENCES) == 9

    def test_denv2_present(self):
        assert "DENV-2" in RDRP_SEQUENCES

    def test_hcv_present(self):
        assert "HCV" in RDRP_SEQUENCES

    def test_all_have_required_fields(self):
        required = {"uniprot_id", "name", "ns5_start", "ns5_end"}
        for virus, info in RDRP_SEQUENCES.items():
            assert required.issubset(info.keys()), f"Missing fields in {virus}"

    def test_all_uniprot_ids_valid_format(self):
        for virus, info in RDRP_SEQUENCES.items():
            uid = info["uniprot_id"]
            assert len(uid) == 6, f"Invalid UniProt ID for {virus}: {uid}"

    def test_ns5_boundaries_reasonable(self):
        for virus, info in RDRP_SEQUENCES.items():
            length = info["ns5_end"] - info["ns5_start"] + 1
            # NS5 should be ~590-905 residues
            assert 500 <= length <= 950, (
                f"Unreasonable NS5 length for {virus}: {length}"
            )


# ─── FASTA parsing tests ──────────────────────────────────────


class TestFastaParser:
    def test_parse_single_sequence(self):
        fasta = ">sp|P29990|POLG_DEN26 Genome polyprotein\nMNDQRKK\nAKNTPFN\n"
        records = parse_fasta(fasta)
        assert len(records) == 1
        assert records[0]["sequence"] == "MNDQRKKAKNTPFN"
        assert "P29990" in records[0]["header"]

    def test_parse_multi_sequence(self):
        fasta = ">seq1\nAAAA\n>seq2\nCCCC\n"
        records = parse_fasta(fasta)
        assert len(records) == 2

    def test_parse_empty(self):
        records = parse_fasta("")
        assert records == []


# ─── Domain extraction tests ──────────────────────────────────


class TestExtractDomain:
    def test_extract_ns5_domain(self):
        fake_seq = "M" * 2491 + "RDRPDOMAIN" + "X" * (3391 - 2501)
        result = extract_ns5_domain(fake_seq, ns5_start=2492, ns5_end=2501)
        assert result == "RDRPDOMAIN"

    def test_extract_handles_bounds(self):
        seq = "ABCDEFGHIJ"
        result = extract_ns5_domain(seq, ns5_start=3, ns5_end=7)
        assert result == "CDEFG"


# ─── Fetch sequence tests ─────────────────────────────────────


class TestFetchSequence:
    @patch("src.conservation.fetch_sequences.http_requests.get")
    def test_fetch_returns_sequence(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = ">sp|P29990|POLG\nMNDQRKKAKNTPFN\n"
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp
        result = fetch_sequence("P29990")
        assert "MNDQRKKAKNTPFN" in result

    @patch("src.conservation.fetch_sequences.http_requests.get")
    def test_fetch_failure_returns_none(self, mock_get):
        mock_get.side_effect = Exception("Network error")
        result = fetch_sequence("INVALID")
        assert result is None


# ─── Alignment parsing tests ──────────────────────────────────


class TestAlignmentParsing:
    def test_parse_fasta_alignment(self):
        aln_text = ">DENV-1\nMNDQ-RKK\n>DENV-2\nMNDQARKK\n"
        result = parse_clustal_alignment(aln_text)
        assert "DENV-1" in result
        assert "DENV-2" in result
        assert result["DENV-1"] == "MNDQ-RKK"
        assert result["DENV-2"] == "MNDQARKK"

    def test_parse_handles_multiline(self):
        aln_text = ">seq1\nAAAA\nBBBB\n>seq2\nCCCC\nDDDD\n"
        result = parse_clustal_alignment(aln_text)
        assert result["seq1"] == "AAAABBBB"
        assert result["seq2"] == "CCCCDDDD"


# ─── Pairwise identity tests ──────────────────────────────────


class TestPairwiseIdentity:
    def test_identical_sequences(self):
        aligned = {"A": "MNDQRKK", "B": "MNDQRKK"}
        matrix = compute_pairwise_identity(aligned)
        assert matrix["A"]["B"] == pytest.approx(100.0)

    def test_different_sequences(self):
        aligned = {"A": "AAAA", "B": "AABB"}
        matrix = compute_pairwise_identity(aligned)
        assert matrix["A"]["B"] == pytest.approx(50.0)

    def test_gap_handling(self):
        aligned = {"A": "AA-A", "B": "AABA"}
        matrix = compute_pairwise_identity(aligned)
        assert matrix["A"]["B"] < 100.0

    def test_self_identity_is_100(self):
        aligned = {"A": "MNDQRKK", "B": "MNAARRR"}
        matrix = compute_pairwise_identity(aligned)
        assert matrix["A"]["A"] == 100.0
        assert matrix["B"]["B"] == 100.0


# ─── Per-position identity tests ──────────────────────────────


class TestPerPositionIdentity:
    def test_fully_conserved(self):
        aligned = {"A": "MMMM", "B": "MMMM", "C": "MMMM"}
        scores = compute_per_position_identity(aligned)
        assert all(s == 100.0 for s in scores)

    def test_variable_position(self):
        aligned = {"A": "MA", "B": "MA", "C": "LA"}
        scores = compute_per_position_identity(aligned)
        assert scores[0] < 100.0  # M vs M vs L
        assert scores[1] == 100.0  # A vs A vs A

    def test_empty_input(self):
        scores = compute_per_position_identity({})
        assert scores == []


# ─── Shannon entropy tests ────────────────────────────────────


class TestShannonEntropy:
    def test_fully_conserved_position(self):
        column = ["A", "A", "A", "A", "A"]
        h = compute_shannon_entropy(column)
        assert h == pytest.approx(0.0)

    def test_fully_variable_position(self):
        column = ["A", "C", "D", "E", "F", "G", "H", "I", "K", "L"]
        h = compute_shannon_entropy(column)
        assert h > 3.0  # log2(10) ≈ 3.32

    def test_two_equal_residues(self):
        column = ["A", "A", "C", "C"]
        h = compute_shannon_entropy(column)
        assert h == pytest.approx(1.0)

    def test_gaps_excluded(self):
        column = ["A", "A", "-", "-", "A"]
        h = compute_shannon_entropy(column)
        assert h == pytest.approx(0.0)

    def test_empty_column(self):
        h = compute_shannon_entropy([])
        assert h == 0.0


# ─── ConSurf normalization tests ──────────────────────────────


class TestConsurfNormalization:
    def test_zero_entropy_gives_nine(self):
        grades = normalize_to_consurf_scale([0.0, 0.0])
        assert all(g == 9 for g in grades)

    def test_high_entropy_gives_one(self):
        grades = normalize_to_consurf_scale([4.0, 4.0])
        assert all(g == 1 for g in grades)

    def test_range_is_1_to_9(self):
        entropies = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0]
        grades = normalize_to_consurf_scale(entropies)
        assert all(1 <= g <= 9 for g in grades)

    def test_empty_input(self):
        grades = normalize_to_consurf_scale([])
        assert grades == []


# ─── Binding site statistical test ─────────────────────────────


class TestBindingSiteTest:
    def test_conserved_binding_site(self):
        all_scores = [9, 9, 9, 9, 9, 3, 4, 5, 2, 3, 4, 5, 6, 3, 2, 4, 5, 3, 4, 5]
        binding_indices = [0, 1, 2, 3, 4]
        result = compute_binding_site_test(all_scores, binding_indices)
        assert result["p_value"] < 0.05
        assert result["binding_mean"] > result["nonbinding_mean"]
        assert result["significant"] is True

    def test_returns_required_keys(self):
        all_scores = [5, 5, 5, 5, 5]
        binding_indices = [0, 1]
        result = compute_binding_site_test(all_scores, binding_indices)
        assert "p_value" in result
        assert "statistic" in result
        assert "significant" in result
        assert "binding_mean" in result
        assert "nonbinding_mean" in result
        assert "n_binding" in result
        assert "n_nonbinding" in result

    def test_empty_binding_site(self):
        result = compute_binding_site_test([5, 5, 5], [])
        assert result["p_value"] == 1.0
        assert result["significant"] is False


# ─── Key residue extraction tests ─────────────────────────────


class TestKeyResidueExtraction:
    def test_extract_conserved_residues(self):
        aligned = {
            "DENV-2": "MNDQRKKD",
            "DENV-1": "MNDQRKKD",
            "ZIKV": "MNDQRKKE",
        }
        rows = extract_key_residue_conservation(aligned, "DENV-2", [8])
        assert len(rows) == 1
        assert rows[0]["reference_aa"] == "D"
        assert rows[0]["DENV-2"] == "D"
        assert rows[0]["ZIKV"] == "E"

    def test_missing_reference(self):
        aligned = {"DENV-1": "AAAA"}
        rows = extract_key_residue_conservation(aligned, "MISSING", [1])
        assert rows == []


# ─── Structure mapping tests ──────────────────────────────────


class TestStructureMapping:
    def test_pymol_script_generation(self):
        script = generate_pymol_script(
            pdb_path="5ZQK_conservation.pdb",
            binding_residues=[533, 663, 664],
        )
        assert "5ZQK_conservation.pdb" in script
        assert "spectrum b" in script
        assert "533" in script

    def test_conservation_viewer_html(self):
        grades = {100: 9, 200: 5, 300: 1}
        html = generate_conservation_viewer_html(
            pdb_id="5ZQK",
            conservation_grades=grades,
            binding_residues=[100],
        )
        assert "3Dmol" in html
        assert "5ZQK" in html

    def test_write_conservation_pdb(self, tmp_path):
        pdb_lines = [
            "ATOM      1  CA  ALA A 100       1.000   2.000   3.000  1.00  0.00           C",
            "ATOM      2  CA  ALA A 200       4.000   5.000   6.000  1.00  0.00           C",
            "END",
        ]
        pdb_text = "\n".join(pdb_lines)
        grades = {100: 9, 200: 5}
        out_path = write_conservation_pdb(pdb_text, grades, tmp_path / "out.pdb")
        assert out_path.exists()
        content = out_path.read_text()
        assert "90.00" in content  # grade 9 * 10
        assert "50.00" in content  # grade 5 * 10

    def test_write_pdb_default_grade(self, tmp_path):
        pdb_lines = [
            "ATOM      1  CA  ALA A 999       1.000   2.000   3.000  1.00  0.00           C",
            "END",
        ]
        pdb_text = "\n".join(pdb_lines)
        grades = {}  # No grades mapped
        out_path = write_conservation_pdb(pdb_text, grades, tmp_path / "out2.pdb")
        content = out_path.read_text()
        assert "50.00" in content  # default grade 5 * 10
