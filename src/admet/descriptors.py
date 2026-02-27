"""Physicochemical descriptors, drug-likeness filters, and structural alerts."""

from __future__ import annotations

from rdkit import Chem
from rdkit.Chem import Descriptors, Lipinski, rdMolDescriptors, FilterCatalog


# ---------------------------------------------------------------------------
# Module-level singleton filter catalogs (built once for performance)
# ---------------------------------------------------------------------------

_pains_params = FilterCatalog.FilterCatalogParams()
_pains_params.AddCatalog(FilterCatalog.FilterCatalogParams.FilterCatalogs.PAINS)
PAINS_CATALOG = FilterCatalog.FilterCatalog(_pains_params)

_brenk_params = FilterCatalog.FilterCatalogParams()
_brenk_params.AddCatalog(FilterCatalog.FilterCatalogParams.FilterCatalogs.BRENK)
BRENK_CATALOG = FilterCatalog.FilterCatalog(_brenk_params)


# ---------------------------------------------------------------------------
# Descriptors
# ---------------------------------------------------------------------------

def compute_descriptors(smiles: str) -> dict | None:
    """Compute physicochemical descriptors for a SMILES string.

    Returns a dict of descriptor values, or None if the SMILES is invalid.
    """
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None

    heavy_atoms = mol.GetNumHeavyAtoms()
    aromatic_atoms = sum(1 for atom in mol.GetAtoms() if atom.GetIsAromatic())
    aromatic_proportion = aromatic_atoms / heavy_atoms if heavy_atoms > 0 else 0.0

    return {
        "mw": Descriptors.MolWt(mol),
        "logp": Descriptors.MolLogP(mol),
        "tpsa": Descriptors.TPSA(mol),
        "hbd": rdMolDescriptors.CalcNumHBD(mol),
        "hba": rdMolDescriptors.CalcNumHBA(mol),
        "rotatable_bonds": rdMolDescriptors.CalcNumRotatableBonds(mol),
        "aromatic_rings": rdMolDescriptors.CalcNumAromaticRings(mol),
        "heavy_atoms": heavy_atoms,
        "fraction_csp3": rdMolDescriptors.CalcFractionCSP3(mol),
        "mol_refractivity": Descriptors.MolMR(mol),
        "aromatic_proportion": aromatic_proportion,
    }


# ---------------------------------------------------------------------------
# Drug-likeness filters
# ---------------------------------------------------------------------------

def check_lipinski(descriptors: dict) -> dict:
    """Lipinski Rule of Five (allows up to 1 violation)."""
    mw_ok = descriptors["mw"] <= 500
    logp_ok = descriptors["logp"] <= 5
    hbd_ok = descriptors["hbd"] <= 5
    hba_ok = descriptors["hba"] <= 10

    violations = sum(not x for x in [mw_ok, logp_ok, hbd_ok, hba_ok])

    return {
        "pass": violations <= 1,
        "violations": violations,
        "mw_ok": mw_ok,
        "logp_ok": logp_ok,
        "hbd_ok": hbd_ok,
        "hba_ok": hba_ok,
    }


def check_veber(descriptors: dict) -> dict:
    """Veber filter for oral bioavailability."""
    tpsa_ok = descriptors["tpsa"] <= 140
    rotbonds_ok = descriptors["rotatable_bonds"] <= 10

    return {
        "pass": tpsa_ok and rotbonds_ok,
        "tpsa_ok": tpsa_ok,
        "rotbonds_ok": rotbonds_ok,
    }


def check_ghose(descriptors: dict) -> dict:
    """Ghose filter for drug-likeness."""
    mw_ok = 160 <= descriptors["mw"] <= 480
    logp_ok = -0.4 <= descriptors["logp"] <= 5.6
    atoms_ok = 20 <= descriptors["heavy_atoms"] <= 70
    mr_ok = 40 <= descriptors["mol_refractivity"] <= 130

    return {
        "pass": all([mw_ok, logp_ok, atoms_ok, mr_ok]),
        "mw_ok": mw_ok,
        "logp_ok": logp_ok,
        "atoms_ok": atoms_ok,
        "mr_ok": mr_ok,
    }


def check_egan(descriptors: dict) -> dict:
    """Egan filter for passive intestinal absorption."""
    tpsa_ok = descriptors["tpsa"] <= 131.6
    logp_ok = descriptors["logp"] <= 5.88

    return {
        "pass": tpsa_ok and logp_ok,
        "tpsa_ok": tpsa_ok,
        "logp_ok": logp_ok,
    }


# ---------------------------------------------------------------------------
# Solubility estimation
# ---------------------------------------------------------------------------

def estimate_esol(descriptors: dict) -> float:
    """Estimate aqueous solubility using the Delaney (ESOL) equation.

    log S = 0.16 - 0.63*logP - 0.0062*MW + 0.066*RB - 0.74*AP

    Returns log S as a float.
    """
    log_s = (
        0.16
        - 0.63 * descriptors["logp"]
        - 0.0062 * descriptors["mw"]
        + 0.066 * descriptors["rotatable_bonds"]
        - 0.74 * descriptors["aromatic_proportion"]
    )
    return float(log_s)


# ---------------------------------------------------------------------------
# Structural alerts
# ---------------------------------------------------------------------------

def check_pains(smiles: str) -> list[str]:
    """Check for PAINS (Pan Assay Interference) substructures.

    Returns a list of matched filter names (empty if clean or invalid SMILES).
    """
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return []

    matches = PAINS_CATALOG.GetMatches(mol)
    return [match.GetDescription() for match in matches]


def check_brenk(smiles: str) -> list[str]:
    """Check for Brenk structural alerts.

    Returns a list of matched filter names (empty if clean or invalid SMILES).
    """
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return []

    matches = BRENK_CATALOG.GetMatches(mol)
    return [match.GetDescription() for match in matches]
