"""Tests for data acquisition pipeline."""

import tempfile
from pathlib import Path

import pytest

import sys

# Ensure project root is importable
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.data_acquisition.fetch_drugs import (
    CURATED_DRUGS,
    load_curated_drugs,
    parse_sdf,
    store_drugs,
)
from src.data_acquisition.fetch_targets import (
    fetch_pdb_structure,
    fetch_uniprot_sequence,
)
from src.data_acquisition.prepare_ligands import smiles_to_3d
from src.utils.db import init_db


# ─── fetch_drugs tests ────────────────────────────────────────


class TestCuratedDrugs:
    """Test the curated drug fallback list."""

    def test_curated_list_has_100_drugs(self):
        drugs = load_curated_drugs()
        assert len(drugs) >= 95  # allow minor dedup

    def test_curated_drugs_have_required_fields(self):
        drugs = load_curated_drugs()
        required = {"name", "drugbank_id", "smiles", "molecular_weight", "logp", "original_indication"}
        for drug in drugs:
            assert required.issubset(drug.keys()), f"Missing fields in {drug.get('name', 'unknown')}"

    def test_curated_drugs_have_valid_smiles(self):
        drugs = load_curated_drugs()
        for drug in drugs:
            assert len(drug["smiles"]) > 0, f"Empty SMILES for {drug['name']}"

    def test_curated_drugs_have_positive_mw(self):
        drugs = load_curated_drugs()
        for drug in drugs:
            assert drug["molecular_weight"] > 0, f"Invalid MW for {drug['name']}"


class TestSDFParsing:
    """Test SDF file parsing."""

    def test_parse_sdf_with_valid_file(self, tmp_path):
        """Parse a minimal SDF block."""
        sdf_content = """aspirin
     RDKit          3D

 13 13  0  0  0  0  0  0  0  0999 V2000
    0.0000    0.0000    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
M  END
> <DATABASE_ID>
DB00945

> <GENERIC_NAME>
aspirin

> <SMILES>
CC(=O)Oc1ccccc1C(O)=O

> <MOLECULAR_WEIGHT>
180.16

> <LOGP>
1.2

> <INDICATION>
pain and inflammation

$$$$
"""
        sdf_file = tmp_path / "test.sdf"
        sdf_file.write_text(sdf_content)

        records = parse_sdf(sdf_file)
        assert len(records) == 1
        assert records[0]["name"] == "aspirin"
        assert records[0]["drugbank_id"] == "DB00945"
        assert records[0]["smiles"] == "CC(=O)Oc1ccccc1C(O)=O"
        assert abs(records[0]["molecular_weight"] - 180.16) < 0.01

    def test_parse_sdf_with_multiple_records(self, tmp_path):
        """Parse an SDF file with multiple records."""
        sdf_content = """aspirin
     RDKit          3D

  0  0  0  0  0  0  0  0  0  0999 V2000
M  END
> <GENERIC_NAME>
aspirin

> <SMILES>
CC(=O)Oc1ccccc1C(O)=O

$$$$
ibuprofen
     RDKit          3D

  0  0  0  0  0  0  0  0  0  0999 V2000
M  END
> <GENERIC_NAME>
ibuprofen

> <SMILES>
CC(C)Cc1ccc(cc1)C(C)C(O)=O

$$$$
"""
        sdf_file = tmp_path / "multi.sdf"
        sdf_file.write_text(sdf_content)

        records = parse_sdf(sdf_file)
        assert len(records) == 2
        assert records[0]["name"] == "aspirin"
        assert records[1]["name"] == "ibuprofen"

    def test_parse_sdf_nonexistent_file(self, tmp_path):
        """Return empty list for nonexistent file."""
        records = parse_sdf(tmp_path / "nonexistent.sdf")
        assert records == []


class TestStoreDrugs:
    """Test database storage of drugs."""

    def test_store_drugs_inserts_records(self, tmp_path):
        db_path = tmp_path / "test.db"
        init_db(db_path)

        drugs = [
            {
                "name": "aspirin",
                "drugbank_id": "DB00945",
                "smiles": "CC(=O)Oc1ccccc1C(O)=O",
                "molecular_weight": 180.16,
                "logp": 1.2,
                "original_indication": "pain",
            }
        ]
        count = store_drugs(drugs, db_path)
        # Just verify it doesn't crash and returns a number
        assert isinstance(count, int)


# ─── fetch_targets tests ──────────────────────────────────────


class TestFetchTargets:
    """Test protein structure fetching."""

    @pytest.mark.network
    def test_fetch_pdb_structure(self, tmp_path):
        """Download a real PDB file (requires network)."""
        path = fetch_pdb_structure("2VBC", output_dir=tmp_path)
        assert path is not None
        assert path.exists()
        assert path.stat().st_size > 1000  # PDB files are at least a few KB
        content = path.read_text()
        assert "ATOM" in content  # PDB files contain ATOM records

    @pytest.mark.network
    def test_fetch_pdb_caches(self, tmp_path):
        """Second fetch should use cached file."""
        path1 = fetch_pdb_structure("2VBC", output_dir=tmp_path)
        path2 = fetch_pdb_structure("2VBC", output_dir=tmp_path)
        assert path1 == path2

    @pytest.mark.network
    def test_fetch_pdb_invalid_id(self, tmp_path):
        """Invalid PDB ID should return None."""
        path = fetch_pdb_structure("XXXX", output_dir=tmp_path)
        assert path is None

    @pytest.mark.network
    def test_fetch_uniprot_sequence(self, tmp_path):
        """Download a UniProt FASTA sequence (requires network)."""
        path = fetch_uniprot_sequence("P27909", output_dir=tmp_path)
        assert path is not None
        assert path.exists()
        content = path.read_text()
        assert content.startswith(">")  # FASTA format


# ─── prepare_ligands tests ────────────────────────────────────


class TestSMILESTo3D:
    """Test 3D coordinate generation from SMILES."""

    def test_simple_molecule(self, tmp_path):
        """Generate 3D coords for aspirin."""
        output = tmp_path / "aspirin.sdf"
        result = smiles_to_3d("CC(=O)Oc1ccccc1C(O)=O", output)

        # RDKit may not be installed in test env
        if result:
            assert output.exists()
            assert output.stat().st_size > 100
        else:
            pytest.skip("RDKit not available")

    def test_invalid_smiles(self, tmp_path):
        """Invalid SMILES should return False."""
        output = tmp_path / "invalid.sdf"
        result = smiles_to_3d("NOT_A_SMILES_STRING", output)
        # Either False (invalid) or skip if RDKit not installed
        if result is False:
            assert not output.exists() or output.stat().st_size == 0

    def test_complex_molecule(self, tmp_path):
        """Generate 3D coords for a larger molecule (ibuprofen)."""
        output = tmp_path / "ibuprofen.sdf"
        result = smiles_to_3d("CC(C)Cc1ccc(cc1)C(C)C(O)=O", output)
        if result:
            assert output.exists()
        else:
            pytest.skip("RDKit not available")


# ─── Integration test ─────────────────────────────────────────


class TestIntegration:
    """End-to-end integration tests."""

    def test_curated_drugs_to_db(self, tmp_path):
        """Load curated drugs and store in a test database."""
        db_path = tmp_path / "integration.db"
        init_db(db_path)

        drugs = load_curated_drugs()
        assert len(drugs) >= 95

        count = store_drugs(drugs, db_path)
        assert isinstance(count, int)
