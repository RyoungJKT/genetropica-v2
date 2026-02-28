"""ML rescoring pipeline with Morgan fingerprints.

Rescores docking results using machine learning. Attempts to load
a DeepChem GNN model; if unavailable, falls back to Morgan
fingerprint + Vina score features with scikit-learn RandomForest.

The Morgan fingerprint approach produces target-specific predictions
because the Vina docking score (which differs per target) is included
as a feature alongside the 2048-bit molecular fingerprint.
"""

import logging
from pathlib import Path
from typing import Optional

import numpy as np

from src.utils.config import DB_PATH
from src.utils.db import get_connection

logger = logging.getLogger(__name__)

_MODEL = None
_BACKEND = None  # "deepchem", "sklearn_chembl", or "sklearn"


def _try_load_chembl_model():
    """Try to load the ChEMBL-trained RandomForest classifier.

    The model was trained on 166 real experimental binding data points
    from ChEMBL (HCV NS5B, Dengue NS5, and Influenza RdRp targets).
    Cross-validation AUC: 0.875 ± 0.094.

    Returns:
        Tuple of (model, backend_name) or (None, None) if not found.
    """
    import pickle

    model_path = Path(__file__).resolve().parents[2] / "models" / "rf_chembl_rdrp.pkl"
    if model_path.exists():
        with open(model_path, "rb") as f:
            model = pickle.load(f)
        logger.info("Loaded ChEMBL-trained RandomForest classifier from %s", model_path)
        return model, "sklearn_chembl"
    return None, None


def _try_load_deepchem():
    """Attempt to load a DeepChem GraphConv model."""
    try:
        import deepchem as dc

        # Try loading a pre-trained binding affinity model
        model_dir = Path(__file__).parent / "models" / "graphconv"
        if model_dir.exists():
            model = dc.models.GraphConvModel(n_tasks=1, mode="regression")
            model.restore(str(model_dir))
            logger.info("Loaded DeepChem GraphConv model")
            return model, "deepchem"
    except (ImportError, Exception) as e:
        logger.info("DeepChem not available: %s", e)
    return None, None


def _build_sklearn_model():
    """Build a fallback RandomForest model using Morgan fingerprints + Vina.

    Uses 2048-bit Morgan fingerprints plus normalised Vina score (2049
    features total) with a RandomForest trained on synthetic binding
    affinity data.

    .. deprecated::
        This is the legacy synthetic-data model. The ChEMBL-trained
        classifier (:func:`_try_load_chembl_model`) is preferred.
    """
    from sklearn.ensemble import RandomForestRegressor

    rng = np.random.RandomState(42)
    n_train = 500
    # 2048 binary fingerprint bits + 1 normalised Vina score
    X_train = rng.randint(0, 2, size=(n_train, 2049)).astype(float)
    # Last column is continuous Vina norm in [0, 1]
    X_train[:, -1] = rng.uniform(0, 1, n_train)
    # Simulate binding: weighted sum of fingerprint bits + vina contribution
    y_train = (
        -5.0
        - 3.0 * X_train[:, -1]
        + 0.5 * X_train[:, :100].sum(axis=1) / 100.0
        + rng.normal(0, 0.5, n_train)
    )
    model = RandomForestRegressor(
        n_estimators=100, max_depth=12, random_state=42, n_jobs=-1,
    )
    model.fit(X_train, y_train)

    logger.info("Built sklearn RandomForest model (2049 features: Morgan FP + Vina)")
    return model, "sklearn"


def load_model():
    """Load the ML scoring model.

    Priority: ChEMBL-trained classifier > DeepChem GNN > synthetic fallback.

    Returns:
        Tuple of (model, backend_name).
    """
    global _MODEL, _BACKEND

    if _MODEL is not None:
        return _MODEL, _BACKEND

    # 1. Try ChEMBL-trained classifier (preferred)
    model, backend = _try_load_chembl_model()

    # 2. Try DeepChem GNN
    if model is None:
        model, backend = _try_load_deepchem()

    # 3. Fall back to synthetic model
    if model is None:
        model, backend = _build_sklearn_model()

    _MODEL, _BACKEND = model, backend
    return model, backend


def _smiles_to_features(
    smiles: str, vina_score: float = 0.0,
) -> Optional[np.ndarray]:
    """Convert SMILES + Vina score to a feature vector.

    Uses a 2048-bit Morgan fingerprint (radius=2) concatenated with
    the normalised Vina docking score.  The Vina component makes the
    feature vector target-specific so that the same drug receives
    different ML predictions for different targets.

    Args:
        smiles: SMILES string.
        vina_score: Vina binding energy (kcal/mol, negative).

    Returns:
        Feature array of shape (2049,), or None if invalid SMILES.
    """
    try:
        from rdkit import Chem
        from rdkit.Chem import AllChem, DataStructs

        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return None

        # Morgan fingerprint (2048-bit, radius 2)
        fp = AllChem.GetMorganFingerprintAsBitVect(mol, radius=2, nBits=2048)
        fp_array = np.zeros(2048)
        DataStructs.ConvertToNumpyArray(fp, fp_array)

        # Normalised Vina score: -12 -> 1.0, -4 -> 0.0
        vina_norm = min(max((vina_score + 4.0) / -8.0, 0.0), 1.0)

        features = np.append(fp_array, vina_norm)
        return features  # shape: (2049,)

    except Exception as e:
        logger.warning("Feature extraction failed for %s: %s", smiles, e)
        return None


def rescore_single(
    drug_smiles: str,
    target_id: str,
    vina_score: float,
) -> Optional[float]:
    """Predict ML binding score for a single drug-target pair.

    Args:
        drug_smiles: SMILES string of the drug.
        target_id: Target identifier.
        vina_score: Original Vina docking score (used as additional feature context).

    Returns:
        ML binding score (float), or None if prediction fails.
    """
    model, backend = load_model()

    features = _smiles_to_features(drug_smiles, vina_score)
    if features is None:
        return None

    try:
        if backend == "sklearn_chembl":
            # ChEMBL classifier: predict_proba gives P(active)
            proba = model.predict_proba(features.reshape(1, -1))[0]
            # proba has [P(inactive), P(active)] — use P(active) as score
            return round(float(proba[1]), 4)
        elif backend == "sklearn":
            # Legacy regressor: predict returns continuous value
            prediction = model.predict(features.reshape(1, -1))[0]
            normalized = min(max((prediction + 12.0) / 8.0, 0.0), 1.0)
            return round(float(normalized), 4)
        else:
            # DeepChem path
            prediction = float(model.predict_on_batch([drug_smiles])[0])
            normalized = min(max((prediction + 12.0) / 8.0, 0.0), 1.0)
            return round(float(normalized), 4)

    except Exception as e:
        logger.warning("ML rescoring failed: %s", e)
        return None


def rescore_batch(
    target_id: str, db_path: Optional[Path] = None,
) -> int:
    """Rescore all drugs for a target and update the database.

    Args:
        target_id: Target identifier.
        db_path: Optional database path override.

    Returns:
        Number of drugs successfully rescored.
    """
    conn = get_connection(db_path)
    count = 0

    try:
        rows = conn.execute(
            """SELECT d.drug_id, d.smiles, dr.vina_score
               FROM drugs d
               JOIN docking_results dr ON d.drug_id = dr.drug_id
               WHERE dr.target_id = ? AND dr.pose_rank = 1
               ORDER BY d.drug_id""",
            (target_id,),
        ).fetchall()

        for row in rows:
            drug_id, smiles, vina_score = row["drug_id"], row["smiles"], row["vina_score"]

            if not smiles:
                continue

            ml_score = rescore_single(smiles, target_id, vina_score)
            if ml_score is None:
                continue

            cons = consensus_score(vina_score, ml_score, target_id=target_id)

            conn.execute(
                """INSERT OR REPLACE INTO ml_scores
                   (drug_id, target_id, ml_binding_score, consensus_score)
                   VALUES (?, ?, ?, ?)""",
                (drug_id, target_id, ml_score, cons),
            )
            count += 1

        conn.commit()
        logger.info("Rescored %d drugs for %s", count, target_id)

    finally:
        conn.close()

    return count


def consensus_score(
    vina_score: float,
    ml_score: float,
    weights: tuple[float, float] = (0.4, 0.6),
    target_id: Optional[str] = None,
) -> float:
    """Calculate weighted consensus score from Vina and ML scores.

    Vina scores are normalized: typical range -12 to -4 kcal/mol
    is mapped to 0-1 (more negative = higher score).

    When *target_id* is provided and *weights* is the default, the
    target-specific weights from
    :data:`consensus_rank.TARGET_WEIGHTS` are used instead.

    Args:
        vina_score: Vina binding energy (kcal/mol, negative).
        ml_score: ML binding score (0-1, higher = better).
        weights: (vina_weight, ml_weight), must sum to 1.0.
        target_id: Optional target identifier for target-specific
            weights.

    Returns:
        Consensus score between 0 and 1 (higher = better candidate).
    """
    if target_id is not None and weights == (0.4, 0.6):
        from src.ai_scoring.consensus_rank import get_target_weights
        weights = get_target_weights(target_id)

    # Normalize Vina: -12 -> 1.0, -4 -> 0.0
    vina_norm = min(max((vina_score + 4.0) / -8.0, 0.0), 1.0)

    return round(weights[0] * vina_norm + weights[1] * ml_score, 4)
