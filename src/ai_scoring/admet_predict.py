"""ADMET toxicity and drug-likeness prediction.

Evaluates Absorption, Distribution, Metabolism, Excretion, and Toxicity
properties using RDKit molecular descriptors. Falls back to heuristic
methods when DeepChem Tox21 models are not available.
"""

import logging
from pathlib import Path
from typing import Optional

from src.utils.db import get_connection

logger = logging.getLogger(__name__)


def predict_lipinski(smiles: str) -> dict:
    """Check Lipinski Rule of Five using RDKit descriptors.

    Rules:
    - Molecular weight <= 500 Da
    - LogP <= 5
    - H-bond donors <= 5
    - H-bond acceptors <= 10

    Args:
        smiles: SMILES string of the molecule.

    Returns:
        Dict with 'mw', 'logp', 'hbd', 'hba', 'pass' (bool),
        and 'violations' (int).
    """
    from rdkit import Chem
    from rdkit.Chem import Descriptors

    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return {"mw": 0, "logp": 0, "hbd": 0, "hba": 0, "pass": False, "violations": 4}

    mw = Descriptors.MolWt(mol)
    logp = Descriptors.MolLogP(mol)
    hbd = Descriptors.NumHDonors(mol)
    hba = Descriptors.NumHAcceptors(mol)

    violations = sum([
        mw > 500,
        logp > 5,
        hbd > 5,
        hba > 10,
    ])

    return {
        "mw": round(mw, 2),
        "logp": round(logp, 2),
        "hbd": hbd,
        "hba": hba,
        "pass": violations <= 1,  # Lipinski allows 1 violation
        "violations": violations,
    }


def predict_toxicity(smiles: str) -> float:
    """Predict hepatotoxicity risk using molecular descriptors.

    Uses RDKit descriptors as heuristic features. Molecules with
    high TPSA, reactive groups, or extreme LogP are flagged.

    Args:
        smiles: SMILES string.

    Returns:
        Hepatotoxicity risk score between 0.0 (safe) and 1.0 (high risk).
    """
    from rdkit import Chem
    from rdkit.Chem import Descriptors

    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return 1.0

    risk = 0.0

    # High molecular weight increases metabolism burden
    mw = Descriptors.MolWt(mol)
    if mw > 600:
        risk += 0.2
    elif mw > 450:
        risk += 0.1

    # Extreme LogP suggests poor metabolism
    logp = Descriptors.MolLogP(mol)
    if logp > 5 or logp < -1:
        risk += 0.2

    # High TPSA can indicate poor membrane permeability / accumulation
    tpsa = Descriptors.TPSA(mol)
    if tpsa > 140:
        risk += 0.15

    # Many rotatable bonds = more metabolic sites
    rot = Descriptors.NumRotatableBonds(mol)
    if rot > 10:
        risk += 0.1

    # Check for reactive substructures (simple patterns)
    reactive_smarts = [
        "[N;X2;v3]=[N;X2;v3]",  # diazo
        "[#6](=[#8])([#8])",      # acid anhydride
        "[N;X1]#[C;X2]",         # isocyanide
    ]
    for sma in reactive_smarts:
        pattern = Chem.MolFromSmarts(sma)
        if pattern and mol.HasSubstructMatch(pattern):
            risk += 0.15

    return round(min(risk, 1.0), 3)


def predict_herg(smiles: str) -> float:
    """Predict hERG potassium channel inhibition risk.

    Uses molecular descriptors correlated with hERG liability:
    high LogP, basic nitrogen atoms, and aromatic rings.

    Args:
        smiles: SMILES string.

    Returns:
        hERG inhibition risk between 0.0 (safe) and 1.0 (high risk).
    """
    from rdkit import Chem
    from rdkit.Chem import Descriptors

    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return 1.0

    risk = 0.0

    # High LogP is a strong predictor of hERG inhibition
    logp = Descriptors.MolLogP(mol)
    if logp > 4:
        risk += 0.3
    elif logp > 3:
        risk += 0.15

    # Basic nitrogen atoms (protonatable at physiological pH)
    basic_n = Chem.MolFromSmarts("[N;!$(N=*);!$(N#*)]")
    if basic_n:
        n_basic = len(mol.GetSubstructMatches(basic_n))
        if n_basic >= 2:
            risk += 0.2
        elif n_basic >= 1:
            risk += 0.1

    # Multiple aromatic rings
    n_arom = Descriptors.NumAromaticRings(mol)
    if n_arom >= 3:
        risk += 0.2
    elif n_arom >= 2:
        risk += 0.1

    # Molecular weight in the hERG-sensitive range
    mw = Descriptors.MolWt(mol)
    if 300 < mw < 600:
        risk += 0.05

    return round(min(risk, 1.0), 3)


def predict_bioavailability(smiles: str) -> float:
    """Estimate oral bioavailability.

    Based on Veber's rules and molecular complexity metrics.
    Drugs with low TPSA, few rotatable bonds, and good lipophilicity
    tend to have higher oral bioavailability.

    Args:
        smiles: SMILES string.

    Returns:
        Bioavailability score between 0.0 (poor) and 1.0 (excellent).
    """
    from rdkit import Chem
    from rdkit.Chem import Descriptors

    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return 0.0

    score = 1.0

    # Veber's rules: TPSA <= 140, rotatable bonds <= 10
    tpsa = Descriptors.TPSA(mol)
    if tpsa > 140:
        score -= 0.3
    elif tpsa > 100:
        score -= 0.1

    rot = Descriptors.NumRotatableBonds(mol)
    if rot > 10:
        score -= 0.25
    elif rot > 7:
        score -= 0.1

    # LogP in ideal range (1-3) for absorption
    logp = Descriptors.MolLogP(mol)
    if logp < -1 or logp > 5:
        score -= 0.2
    elif logp < 0 or logp > 4:
        score -= 0.1

    # Molecular weight penalty
    mw = Descriptors.MolWt(mol)
    if mw > 500:
        score -= 0.15
    elif mw > 400:
        score -= 0.05

    return round(max(score, 0.0), 3)


def full_admet_profile(smiles: str) -> dict:
    """Run all ADMET predictions for a single molecule.

    Args:
        smiles: SMILES string.

    Returns:
        Dict with keys: lipinski_pass, hepatotoxicity_risk,
        herg_inhibition_risk, oral_bioavailability, overall_pass.
    """
    lip = predict_lipinski(smiles)
    hep = predict_toxicity(smiles)
    herg = predict_herg(smiles)
    bio = predict_bioavailability(smiles)

    overall = all([
        lip["pass"],
        hep < 0.5,
        herg < 0.5,
        bio >= 0.5,
    ])

    return {
        "lipinski_pass": lip["pass"],
        "hepatotoxicity_risk": hep,
        "herg_inhibition_risk": herg,
        "oral_bioavailability": bio,
        "overall_pass": overall,
    }


def batch_admet(
    drug_list: Optional[list[dict]] = None,
    db_path: Optional[Path] = None,
) -> int:
    """Run ADMET predictions for all drugs and store in database.

    Args:
        drug_list: Optional list of dicts with 'drug_id' and 'smiles'.
            If None, reads from database.
        db_path: Optional database path override.

    Returns:
        Number of drugs processed.
    """
    conn = get_connection(db_path)
    count = 0

    try:
        if drug_list is None:
            rows = conn.execute(
                "SELECT drug_id, smiles FROM drugs WHERE smiles IS NOT NULL"
            ).fetchall()
            drug_list = [{"drug_id": r["drug_id"], "smiles": r["smiles"]} for r in rows]

        for drug in drug_list:
            drug_id = drug["drug_id"]
            smiles = drug.get("smiles")

            if not smiles:
                continue

            profile = full_admet_profile(smiles)

            conn.execute(
                """INSERT OR REPLACE INTO admet
                   (drug_id, lipinski_pass, hepatotoxicity_risk,
                    herg_inhibition_risk, oral_bioavailability, overall_pass)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    drug_id,
                    profile["lipinski_pass"],
                    profile["hepatotoxicity_risk"],
                    profile["herg_inhibition_risk"],
                    profile["oral_bioavailability"],
                    profile["overall_pass"],
                ),
            )
            count += 1

        conn.commit()
        logger.info("ADMET predictions complete for %d drugs", count)

    finally:
        conn.close()

    return count
