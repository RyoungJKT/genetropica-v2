"""Regression tests for the data-integrity remediation (FIX-1, FIX-3, FIX-6).

These guard against the structure/molecular-weight corruption returning.
Run:  python -m pytest tests/test_data_integrity.py -q
"""
import sqlite3
from pathlib import Path

import pytest
from rdkit import Chem
from rdkit.Chem import Descriptors
from rdkit import RDLogger

RDLogger.DisableLog("rdApp.*")

DB = Path(__file__).resolve().parents[1] / "data" / "database" / "genetropica.db"


@pytest.fixture(scope="module")
def drugs():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    rows = [dict(r) for r in con.execute(
        "SELECT name, smiles, molecular_weight, heavy_atoms, inchikey, ref_mw FROM drugs"
    )]
    con.close()
    assert rows, "no drugs in database"
    return rows


# ── FIX-1 ──────────────────────────────────────────────────────────────

def test_stored_mw_matches_structure(drugs):
    """Stored MW is recomputed from the stored SMILES (no orphan values)."""
    bad = []
    for d in drugs:
        m = Chem.MolFromSmiles(d["smiles"])
        assert m is not None, f"unparseable SMILES for {d['name']}"
        if abs(Descriptors.MolWt(m) - d["molecular_weight"]) / d["molecular_weight"] > 0.01:
            bad.append((d["name"], round(Descriptors.MolWt(m), 1), d["molecular_weight"]))
    assert not bad, f"stored MW disagrees with structure: {bad}"


def test_stored_mw_within_1pct_of_reference(drugs):
    """Every drug's MW is within 1% of the PubChem reference MW."""
    bad = [d["name"] for d in drugs
           if d["ref_mw"] and abs(d["molecular_weight"] - d["ref_mw"]) / d["ref_mw"] > 0.01]
    assert not bad, f"MW deviates >1% from PubChem reference: {bad}"


def test_heavy_atoms_match_structure(drugs):
    bad = [d["name"] for d in drugs
           if Chem.MolFromSmiles(d["smiles"]).GetNumHeavyAtoms() != d["heavy_atoms"]]
    assert not bad, f"heavy_atoms disagrees with structure: {bad}"


def test_known_large_molecule_corrections(drugs):
    by = {d["name"]: d for d in drugs}
    assert by["pibrentasvir"]["molecular_weight"] > 1000, "pibrentasvir should be ~1113"
    assert 740 < by["paritaprevir"]["molecular_weight"] < 790, "paritaprevir should be ~766"
    assert by["ledipasvir"]["molecular_weight"] != by["ombitasvir"]["molecular_weight"], (
        "ledipasvir and ombitasvir are different molecules and must not share an MW"
    )


def test_no_duplicate_structures(drugs):
    """No two chemically distinct drugs share the same connectivity (InChIKey block 1)."""
    seen, dups = {}, []
    for d in drugs:
        if not d["inchikey"]:
            continue
        key = d["inchikey"].split("-")[0]
        if key in seen and seen[key] != d["name"]:
            dups.append((seen[key], d["name"]))
        else:
            seen[key] = d["name"]
    assert not dups, f"distinct drugs share a structure: {dups}"
