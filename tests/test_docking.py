"""Tests for molecular docking pipeline."""

import tempfile
from pathlib import Path

import pytest

from src.docking.prepare_receptor import (
    BINDING_SITES,
    SearchBox,
    clean_pdb,
    define_search_box,
)
from src.docking.parse_results import parse_vina_output
from src.docking.interaction_analysis import (
    _classify_interaction,
    _distance,
    _parse_coordinates,
    _parse_residue_info,
    analyze_interactions,
)
from src.utils.db import get_connection, init_db


# ─── Sample data ──────────────────────────────────────────

SAMPLE_PDB = """\
HEADER    TEST PROTEIN
ATOM      1  N   ALA A   1       1.000   2.000   3.000  1.00  0.00           N
ATOM      2  CA  ALA A   1       2.000   3.000   4.000  1.00  0.00           C
ATOM      3  C   ALA A   1       3.000   4.000   5.000  1.00  0.00           C
HETATM    4  O   HOH A 101      10.000  10.000  10.000  1.00  0.00           O
TER
END
"""

SAMPLE_VINA_OUTPUT = """\
MODEL 1
REMARK VINA RESULT:    -8.50      0.000      0.000
ATOM      1  C1  LIG A   1       5.000   6.000   7.000  1.00  0.00           C
ATOM      2  O1  LIG A   1       5.500   6.500   7.500  1.00  0.00           O
ENDMDL
MODEL 2
REMARK VINA RESULT:    -7.20      0.000      0.000
ATOM      1  C1  LIG A   1       6.000   7.000   8.000  1.00  0.00           C
ATOM      2  O1  LIG A   1       6.500   7.500   8.500  1.00  0.00           O
ENDMDL
MODEL 3
REMARK VINA RESULT:    -6.10      0.000      0.000
ATOM      1  C1  LIG A   1       7.000   8.000   9.000  1.00  0.00           C
ENDMDL
"""

# Receptor and ligand with atoms close enough for interactions
RECEPTOR_FOR_INTERACTIONS = """\
ATOM      1  N   SER A  10       1.000   2.000   3.000  1.00  0.00           N
ATOM      2  OG  SER A  10       1.500   2.500   3.500  1.00  0.00           O
ATOM      3  CB  PHE A  20       5.000   5.000   5.000  1.00  0.00           C
ATOM      4  CG  PHE A  20       5.200   5.200   5.200  1.00  0.00           C
ATOM      5  NZ  LYS A  30       8.000   8.000   8.000  1.00  0.00           N
ATOM      6  CB  LEU A  40       2.000   3.000   4.000  1.00  0.00           C
END
"""

LIGAND_FOR_INTERACTIONS = """\
ATOM      1  C1  LIG A   1       1.200   2.200   3.200  1.00  0.00           C
ATOM      2  O1  LIG A   1       1.800   2.800   3.800  1.00  0.00           O
ATOM      3  C2  LIG A   1       5.100   5.100   5.100  1.00  0.00           C
END
"""


# ─── Test receptor preparation ────────────────────────────


class TestCleanPDB:
    def test_removes_hetatm_and_water(self, tmp_path):
        pdb_file = tmp_path / "test.pdb"
        pdb_file.write_text(SAMPLE_PDB)

        clean_path = clean_pdb(pdb_file)

        assert clean_path.exists()
        content = clean_path.read_text()
        assert "HETATM" not in content
        assert "HOH" not in content
        assert "ATOM" in content
        assert "TER" in content
        assert "END" in content

    def test_output_filename(self, tmp_path):
        pdb_file = tmp_path / "protein.pdb"
        pdb_file.write_text(SAMPLE_PDB)

        clean_path = clean_pdb(pdb_file)
        assert clean_path.name == "protein_clean.pdb"

    def test_custom_output_path(self, tmp_path):
        pdb_file = tmp_path / "test.pdb"
        pdb_file.write_text(SAMPLE_PDB)
        out = tmp_path / "custom_clean.pdb"

        result = clean_pdb(pdb_file, output_path=out)
        assert result == out
        assert out.exists()

    def test_line_count(self, tmp_path):
        pdb_file = tmp_path / "test.pdb"
        pdb_file.write_text(SAMPLE_PDB)

        clean_path = clean_pdb(pdb_file)
        lines = clean_path.read_text().strip().split("\n")
        # 3 ATOM + 1 TER + 1 END = 5 lines
        assert len(lines) == 5


class TestSearchBox:
    def test_default_size(self):
        box = SearchBox(center_x=1.0, center_y=2.0, center_z=3.0)
        assert box.size_x == 25.0
        assert box.size_y == 25.0
        assert box.size_z == 25.0

    def test_binding_sites_defined(self):
        expected = {"DENV_NS3", "DENV_NS5", "DENV_E", "CHIKV_nsP2", "CHIKV_nsP1", "LEPTO_LipL32"}
        assert set(BINDING_SITES.keys()) == expected

    def test_define_known_target(self):
        box = define_search_box("DENV_NS3")
        assert box.center_x == 15.0
        assert box.center_y == 45.0
        assert box.center_z == 30.0

    def test_define_unknown_target(self):
        box = define_search_box("UNKNOWN_TARGET")
        assert box.center_x == 0.0
        assert box.size_x == 30.0

    def test_custom_center_override(self):
        box = define_search_box("DENV_NS3", center=(99.0, 88.0, 77.0))
        assert box.center_x == 99.0
        assert box.center_y == 88.0
        assert box.center_z == 77.0

    def test_custom_size_override(self):
        box = define_search_box("DENV_NS3", size=(10.0, 20.0, 30.0))
        assert box.size_x == 10.0
        assert box.size_y == 20.0
        assert box.size_z == 30.0


# ─── Test Vina output parsing ────────────────────────────


class TestParseVinaOutput:
    def test_parses_three_poses(self, tmp_path):
        out_file = tmp_path / "test_out.pdbqt"
        out_file.write_text(SAMPLE_VINA_OUTPUT)

        poses = parse_vina_output(out_file)
        assert len(poses) == 3

    def test_scores_extracted(self, tmp_path):
        out_file = tmp_path / "test_out.pdbqt"
        out_file.write_text(SAMPLE_VINA_OUTPUT)

        poses = parse_vina_output(out_file)
        assert poses[0]["vina_score"] == -8.50
        assert poses[1]["vina_score"] == -7.20
        assert poses[2]["vina_score"] == -6.10

    def test_pose_ranks(self, tmp_path):
        out_file = tmp_path / "test_out.pdbqt"
        out_file.write_text(SAMPLE_VINA_OUTPUT)

        poses = parse_vina_output(out_file)
        assert poses[0]["pose_rank"] == 1
        assert poses[1]["pose_rank"] == 2
        assert poses[2]["pose_rank"] == 3

    def test_atoms_captured(self, tmp_path):
        out_file = tmp_path / "test_out.pdbqt"
        out_file.write_text(SAMPLE_VINA_OUTPUT)

        poses = parse_vina_output(out_file)
        assert len(poses[0]["atoms"]) == 2  # 2 ATOM lines in model 1
        assert len(poses[2]["atoms"]) == 1  # 1 ATOM line in model 3

    def test_nonexistent_file(self, tmp_path):
        poses = parse_vina_output(tmp_path / "nonexistent.pdbqt")
        assert poses == []


# ─── Test interaction analysis ────────────────────────────


class TestInteractionHelpers:
    def test_parse_coordinates(self):
        line = "ATOM      1  N   ALA A   1       1.000   2.000   3.000  1.00  0.00           N"
        coords = _parse_coordinates(line)
        assert coords == (1.0, 2.0, 3.0)

    def test_parse_coordinates_short_line(self):
        assert _parse_coordinates("SHORT") is None

    def test_parse_residue_info(self):
        line = "ATOM      1  CA  ALA A   1       1.000   2.000   3.000  1.00  0.00           C"
        info = _parse_residue_info(line)
        assert info["residue_name"] == "ALA"
        assert info["residue_number"] == 1
        assert info["chain"] == "A"
        assert info["atom_name"] == "CA"

    def test_distance(self):
        d = _distance((0, 0, 0), (3, 4, 0))
        assert abs(d - 5.0) < 0.001

    def test_distance_same_point(self):
        assert _distance((1, 2, 3), (1, 2, 3)) == 0.0


class TestClassifyInteraction:
    def test_hydrogen_bond(self):
        result = _classify_interaction("SER", 3.0, "OG")
        assert result == "Hydrogen Bond"

    def test_hydrophobic(self):
        result = _classify_interaction("LEU", 4.0, "CB")
        assert result == "Hydrophobic"

    def test_pi_stacking(self):
        result = _classify_interaction("PHE", 5.0, "CG")
        assert result == "Pi-Stacking"

    def test_salt_bridge(self):
        # Distance > 3.5 (H-bond cutoff) but < 4.0 (ionic cutoff)
        result = _classify_interaction("ASP", 3.8, "OD1")
        assert result == "Ionic"

    def test_no_interaction_too_far(self):
        result = _classify_interaction("ALA", 10.0, "CA")
        assert result is None


class TestAnalyzeInteractions:
    def test_finds_interactions(self, tmp_path):
        rec = tmp_path / "receptor.pdb"
        lig = tmp_path / "ligand.pdb"
        rec.write_text(RECEPTOR_FOR_INTERACTIONS)
        lig.write_text(LIGAND_FOR_INTERACTIONS)

        interactions = analyze_interactions(rec, lig)
        assert len(interactions) > 0

    def test_interaction_structure(self, tmp_path):
        rec = tmp_path / "receptor.pdb"
        lig = tmp_path / "ligand.pdb"
        rec.write_text(RECEPTOR_FOR_INTERACTIONS)
        lig.write_text(LIGAND_FOR_INTERACTIONS)

        interactions = analyze_interactions(rec, lig)
        if interactions:
            inter = interactions[0]
            assert "residue_name" in inter
            assert "residue_number" in inter
            assert "chain" in inter
            assert "interaction_type" in inter
            assert "distance" in inter

    def test_empty_files(self, tmp_path):
        rec = tmp_path / "empty_rec.pdb"
        lig = tmp_path / "empty_lig.pdb"
        rec.write_text("")
        lig.write_text("")

        interactions = analyze_interactions(rec, lig)
        assert interactions == []

    def test_nonexistent_files(self, tmp_path):
        interactions = analyze_interactions(
            tmp_path / "nope.pdb", tmp_path / "also_nope.pdb"
        )
        assert interactions == []


# ─── Test mock pipeline ──────────────────────────────────


class TestMockPipeline:
    def test_mock_docking_stores_results(self, tmp_path):
        """Test that mock docking generates and stores results."""
        from scripts.run_pipeline import generate_mock_docking

        db_path = tmp_path / "test.db"
        init_db(db_path)

        # Insert a few test drugs
        conn = get_connection(db_path)
        try:
            for i in range(3):
                conn.execute(
                    "INSERT INTO drugs (drug_id, name) VALUES (?, ?)",
                    (f"DRUG_{i:03d}", f"Test Drug {i}"),
                )
            for tid in ["DENV_NS3"]:
                conn.execute(
                    "INSERT INTO targets (target_id, name, disease) VALUES (?, ?, ?)",
                    (tid, "NS3", "Dengue"),
                )
            conn.commit()
        finally:
            conn.close()

        # Patch DB_PATH in both config and db modules
        import src.utils.config as cfg
        import src.utils.db as db_mod
        orig_cfg = cfg.DB_PATH
        orig_db = db_mod.DB_PATH
        cfg.DB_PATH = db_path
        db_mod.DB_PATH = db_path
        try:
            generate_mock_docking("DENV_NS3", n_drugs=3, n_poses=3)

            conn = get_connection(db_path)
            try:
                count = conn.execute(
                    "SELECT COUNT(*) FROM docking_results WHERE target_id = 'DENV_NS3'"
                ).fetchone()[0]
                assert count == 9  # 3 drugs x 3 poses
            finally:
                conn.close()
        finally:
            cfg.DB_PATH = orig_cfg
            db_mod.DB_PATH = orig_db

    def test_resolve_pdb_id(self):
        from scripts.run_pipeline import _resolve_target

        assert _resolve_target("DENV_NS3") == "DENV_NS3"
        assert _resolve_target("2VBC") == "DENV_NS3"
        assert _resolve_target("2vbc") == "DENV_NS3"
        assert _resolve_target("NONEXISTENT") is None
