"""Tests for AI structure prediction module."""

import json
from pathlib import Path

import pytest

from src.structure_prediction.esmfold_predict import (
    extract_mean_plddt,
    extract_plddt_per_residue,
    _read_fasta,
)
from src.structure_prediction.colabfold_runner import (
    generate_colabfold_notebook,
    parse_colabfold_output,
)
from src.structure_prediction.validate_structure import (
    check_clashes,
    check_plddt,
    compare_to_experimental,
    generate_quality_report,
    is_suitable_for_docking,
)


# ─── Sample data ──────────────────────────────────────────

# Sample PDB with pLDDT scores in B-factor column (ESMFold-style)
SAMPLE_PREDICTED_PDB = """\
ATOM      1  N   ALA A   1       1.000   2.000   3.000  1.00 85.20           N
ATOM      2  CA  ALA A   1       2.000   3.000   4.000  1.00 85.20           C
ATOM      3  C   ALA A   1       3.000   4.000   5.000  1.00 85.20           C
ATOM      4  N   GLY A   2       4.000   5.000   6.000  1.00 92.10           N
ATOM      5  CA  GLY A   2       5.000   6.000   7.000  1.00 92.10           C
ATOM      6  C   GLY A   2       6.000   7.000   8.000  1.00 92.10           C
ATOM      7  N   SER A   3       7.000   8.000   9.000  1.00 78.50           N
ATOM      8  CA  SER A   3       8.000   9.000  10.000  1.00 78.50           C
ATOM      9  C   SER A   3       9.000  10.000  11.000  1.00 78.50           C
ATOM     10  N   LEU A   4      10.000  11.000  12.000  1.00 45.30           N
ATOM     11  CA  LEU A   4      11.000  12.000  13.000  1.00 45.30           C
ATOM     12  C   LEU A   4      12.000  13.000  14.000  1.00 45.30           C
ATOM     13  N   PHE A   5      13.000  14.000  15.000  1.00 91.00           N
ATOM     14  CA  PHE A   5      14.000  15.000  16.000  1.00 91.00           C
ATOM     15  C   PHE A   5      15.000  16.000  17.000  1.00 91.00           C
END
"""

# Low-confidence predicted PDB
LOW_PLDDT_PDB = """\
ATOM      1  N   ALA A   1       1.000   2.000   3.000  1.00 35.00           N
ATOM      2  CA  ALA A   1       2.000   3.000   4.000  1.00 35.00           C
ATOM      3  N   GLY A   2       4.000   5.000   6.000  1.00 40.00           N
ATOM      4  CA  GLY A   2       5.000   6.000   7.000  1.00 40.00           C
ATOM      5  N   SER A   3       7.000   8.000   9.000  1.00 30.00           N
ATOM      6  CA  SER A   3       8.000   9.000  10.000  1.00 30.00           C
END
"""

# PDB with atoms close enough to clash
CLASHING_PDB = """\
ATOM      1  N   ALA A   1       1.000   1.000   1.000  1.00 80.00           N
ATOM      2  CA  ALA A   1       1.500   1.000   1.000  1.00 80.00           C
ATOM      3  N   GLY A   5       1.100   1.100   1.100  1.00 80.00           N
ATOM      4  CA  GLY A   5       1.600   1.100   1.100  1.00 80.00           C
END
"""

SAMPLE_FASTA = """\
>sp|P27909|DENV_NS3
MKFLVNVALVFM
GKLLKPGGGGS
"""


# ─── pLDDT extraction tests ──────────────────────────────


class TestPLDDT:
    def test_extract_plddt_per_residue(self, tmp_path):
        pdb = tmp_path / "pred.pdb"
        pdb.write_text(SAMPLE_PREDICTED_PDB)

        values = extract_plddt_per_residue(pdb)
        assert len(values) == 5  # 5 CA atoms
        assert values[0] == 85.20
        assert values[1] == 92.10
        assert values[3] == 45.30

    def test_extract_mean_plddt(self, tmp_path):
        pdb = tmp_path / "pred.pdb"
        pdb.write_text(SAMPLE_PREDICTED_PDB)

        mean = extract_mean_plddt(pdb)
        expected = (85.20 + 92.10 + 78.50 + 45.30 + 91.00) / 5
        assert abs(mean - expected) < 0.01

    def test_empty_file_plddt(self, tmp_path):
        pdb = tmp_path / "empty.pdb"
        pdb.write_text("")

        values = extract_plddt_per_residue(pdb)
        assert values == []
        assert extract_mean_plddt(pdb) == 0.0

    def test_nonexistent_file(self, tmp_path):
        values = extract_plddt_per_residue(tmp_path / "nope.pdb")
        assert values == []


class TestCheckPLDDT:
    def test_full_report(self, tmp_path):
        pdb = tmp_path / "pred.pdb"
        pdb.write_text(SAMPLE_PREDICTED_PDB)

        result = check_plddt(pdb)
        assert result["n_residues"] == 5
        assert result["mean_plddt"] > 0
        assert result["median_plddt"] > 0
        assert "pct_confident" in result
        assert "pct_very_confident" in result

    def test_confident_percentage(self, tmp_path):
        pdb = tmp_path / "pred.pdb"
        pdb.write_text(SAMPLE_PREDICTED_PDB)

        result = check_plddt(pdb)
        # 4 of 5 residues have pLDDT >= 70 (all except LEU at 45.3)
        assert result["pct_confident"] == 80.0

    def test_very_confident_percentage(self, tmp_path):
        pdb = tmp_path / "pred.pdb"
        pdb.write_text(SAMPLE_PREDICTED_PDB)

        result = check_plddt(pdb)
        # 2 of 5 have pLDDT >= 90 (GLY at 92.1 and PHE at 91.0)
        assert result["pct_very_confident"] == 40.0

    def test_empty_pdb(self, tmp_path):
        pdb = tmp_path / "empty.pdb"
        pdb.write_text("")

        result = check_plddt(pdb)
        assert result["n_residues"] == 0
        assert result["mean_plddt"] == 0.0


# ─── Clash detection tests ───────────────────────────────


class TestClashDetection:
    def test_no_clashes_normal_pdb(self, tmp_path):
        pdb = tmp_path / "normal.pdb"
        pdb.write_text(SAMPLE_PREDICTED_PDB)

        result = check_clashes(pdb)
        assert result["n_atoms"] > 0
        assert result["n_clashes"] == 0

    def test_detects_clashes(self, tmp_path):
        pdb = tmp_path / "clashing.pdb"
        pdb.write_text(CLASHING_PDB)

        result = check_clashes(pdb, threshold=1.5)
        assert result["n_atoms"] == 4
        # Atoms from residues 1 and 5 are very close (~0.17 A)
        assert result["n_clashes"] > 0

    def test_empty_file(self, tmp_path):
        pdb = tmp_path / "empty.pdb"
        pdb.write_text("")

        result = check_clashes(pdb)
        assert result["n_clashes"] == 0
        assert result["n_atoms"] == 0


# ─── RMSD comparison tests ───────────────────────────────


class TestRMSD:
    def test_identical_structures(self, tmp_path):
        pdb = tmp_path / "struct.pdb"
        pdb.write_text(SAMPLE_PREDICTED_PDB)

        result = compare_to_experimental(pdb, pdb)
        assert result["rmsd"] == 0.0
        assert result["n_aligned"] == 5
        assert result["quality"] == "excellent"

    def test_different_structures(self, tmp_path):
        pred = tmp_path / "pred.pdb"
        pred.write_text(SAMPLE_PREDICTED_PDB)

        # Create shifted version
        shifted = SAMPLE_PREDICTED_PDB.replace("2.000   3.000   4.000", "5.000   6.000   7.000")
        exp = tmp_path / "exp.pdb"
        exp.write_text(shifted)

        result = compare_to_experimental(pred, exp)
        assert result["rmsd"] > 0
        assert result["n_aligned"] > 0

    def test_missing_file(self, tmp_path):
        pred = tmp_path / "pred.pdb"
        pred.write_text(SAMPLE_PREDICTED_PDB)

        result = compare_to_experimental(pred, tmp_path / "missing.pdb")
        assert result["rmsd"] == float("inf")
        assert result["n_aligned"] == 0


# ─── Quality report tests ────────────────────────────────


class TestQualityReport:
    def test_good_structure(self, tmp_path):
        pdb = tmp_path / "pred.pdb"
        pdb.write_text(SAMPLE_PREDICTED_PDB)

        report = generate_quality_report(pdb)
        assert "plddt" in report
        assert "clashes" in report
        assert "suitable_for_docking" in report
        assert "recommendation" in report

    def test_suitable_structure(self, tmp_path):
        pdb = tmp_path / "pred.pdb"
        pdb.write_text(SAMPLE_PREDICTED_PDB)

        report = generate_quality_report(pdb)
        # Mean pLDDT ~78.4, 80% confident, 0 clashes -> suitable
        assert report["suitable_for_docking"] is True

    def test_low_quality_structure(self, tmp_path):
        pdb = tmp_path / "low.pdb"
        pdb.write_text(LOW_PLDDT_PDB)

        report = generate_quality_report(pdb)
        assert report["suitable_for_docking"] is False


class TestDockingSuitability:
    def test_good_structure_suitable(self, tmp_path):
        pdb = tmp_path / "pred.pdb"
        pdb.write_text(SAMPLE_PREDICTED_PDB)

        assert is_suitable_for_docking(pdb) is True

    def test_low_plddt_not_suitable(self, tmp_path):
        pdb = tmp_path / "low.pdb"
        pdb.write_text(LOW_PLDDT_PDB)

        assert is_suitable_for_docking(pdb) is False

    def test_empty_not_suitable(self, tmp_path):
        pdb = tmp_path / "empty.pdb"
        pdb.write_text("")

        assert is_suitable_for_docking(pdb) is False


# ─── ColabFold notebook tests ────────────────────────────


class TestColabFold:
    def test_generate_notebook(self, tmp_path):
        seq = "MKFLVNVALVFMGKLLKPGGGGS"
        path = generate_colabfold_notebook(seq, output_dir=tmp_path, job_name="test")

        assert path.exists()
        assert path.suffix == ".ipynb"

        with open(path) as f:
            nb = json.load(f)
        assert nb["nbformat"] == 4
        assert len(nb["cells"]) == 5

    def test_notebook_contains_sequence(self, tmp_path):
        seq = "MKFLVNVALVFM"
        path = generate_colabfold_notebook(seq, output_dir=tmp_path, job_name="seqtest")

        content = path.read_text()
        assert seq in content

    def test_parse_empty_dir(self, tmp_path):
        result = parse_colabfold_output(tmp_path)
        assert result is None

    def test_parse_with_pdb(self, tmp_path):
        # Create a fake ColabFold output
        pdb_file = tmp_path / "test_unrelaxed_rank_001_model_1.pdb"
        pdb_file.write_text(SAMPLE_PREDICTED_PDB)

        result = parse_colabfold_output(tmp_path)
        assert result is not None
        assert result.name == pdb_file.name


# ─── FASTA reading test ──────────────────────────────────


class TestFastaReading:
    def test_read_fasta(self, tmp_path):
        fasta = tmp_path / "test.fasta"
        fasta.write_text(SAMPLE_FASTA)

        seq = _read_fasta(fasta)
        assert seq == "MKFLVNVALVFMGKLLKPGGGGS"

    def test_read_fasta_no_header(self, tmp_path):
        fasta = tmp_path / "nohdr.fasta"
        fasta.write_text("MKFLV\nNVALV\n")

        seq = _read_fasta(fasta)
        assert seq == "MKFLVNVALV"


# ─── ESMFold API test (network) ──────────────────────────


class TestESMFoldAPI:
    @pytest.mark.network
    def test_predict_short_peptide(self, tmp_path):
        from src.structure_prediction.esmfold_predict import predict_structure

        # Very short peptide for fast API test
        result = predict_structure(
            "MKFLVNVALVFM",
            output_path=tmp_path / "test_esmfold.pdb",
            name="test_peptide",
        )
        if result is not None:
            assert result.exists()
            plddt = extract_mean_plddt(result)
            assert plddt > 0
