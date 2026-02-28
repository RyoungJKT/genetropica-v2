"""SQLite database operations for GeneTropica."""

import logging
import sqlite3
from pathlib import Path
from typing import Optional

import pandas as pd

from src.utils.config import DB_PATH

logger = logging.getLogger(__name__)

_SCHEMA_SQL = """
-- Drug library
CREATE TABLE IF NOT EXISTS drugs (
    drug_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    drugbank_id TEXT,
    original_indication TEXT,
    smiles TEXT,
    molecular_weight REAL,
    logp REAL,
    pdbqt_path TEXT
);

-- Protein targets
CREATE TABLE IF NOT EXISTS targets (
    target_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    disease TEXT NOT NULL,
    pdb_id TEXT,
    uniprot_id TEXT,
    structure_source TEXT,
    pdbqt_path TEXT
);

-- Docking results
CREATE TABLE IF NOT EXISTS docking_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    drug_id TEXT REFERENCES drugs(drug_id),
    target_id TEXT REFERENCES targets(target_id),
    vina_score REAL,
    pose_rank INTEGER,
    pose_path TEXT,
    UNIQUE(drug_id, target_id, pose_rank)
);

-- ML rescoring results
CREATE TABLE IF NOT EXISTS ml_scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    drug_id TEXT REFERENCES drugs(drug_id),
    target_id TEXT REFERENCES targets(target_id),
    ml_binding_score REAL,
    consensus_score REAL,
    consensus_rank INTEGER
);

-- ADMET predictions
CREATE TABLE IF NOT EXISTS admet (
    drug_id TEXT PRIMARY KEY REFERENCES drugs(drug_id),
    lipinski_pass BOOLEAN,
    hepatotoxicity_risk REAL,
    herg_inhibition_risk REAL,
    oral_bioavailability REAL,
    overall_pass BOOLEAN
);

-- Literature evidence
CREATE TABLE IF NOT EXISTS literature (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    drug_id TEXT REFERENCES drugs(drug_id),
    target_id TEXT REFERENCES targets(target_id),
    pmid TEXT,
    title TEXT,
    relationship TEXT,
    confidence REAL,
    UNIQUE(drug_id, target_id, pmid)
);

-- Protein-ligand interactions
CREATE TABLE IF NOT EXISTS interactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    drug_id TEXT REFERENCES drugs(drug_id),
    target_id TEXT REFERENCES targets(target_id),
    pose_rank INTEGER,
    residue_name TEXT,
    residue_number INTEGER,
    chain TEXT,
    interaction_type TEXT,
    distance REAL
);
"""


def get_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """Get a connection to the SQLite database.

    Args:
        db_path: Optional path override. Defaults to DB_PATH from config.

    Returns:
        Active SQLite connection with foreign keys enabled.
    """
    path = db_path or DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Optional[Path] = None) -> None:
    """Initialize the database by creating all tables.

    Args:
        db_path: Optional path override. Defaults to DB_PATH from config.
    """
    conn = get_connection(db_path)
    try:
        conn.executescript(_SCHEMA_SQL)
        conn.commit()
        logger.info("Database initialized at %s", db_path or DB_PATH)
    finally:
        conn.close()


# ─── Query helpers for the dashboard ────────────────────────


def _query_df(sql: str, params: tuple = ()) -> pd.DataFrame:
    """Execute a read query and return results as a DataFrame."""
    conn = get_connection()
    try:
        df = pd.read_sql_query(sql, conn, params=params)
        return df
    finally:
        conn.close()


def get_drugs_for_target(target_id: str) -> pd.DataFrame:
    """Get all drugs with scores and ADMET status for a given target.

    Returns a DataFrame with columns: drug_id, name, drugbank_id,
    original_indication, vina_score, ml_binding_score, consensus_score,
    consensus_rank, lipinski_pass, overall_pass, lit_count.
    """
    return _query_df(
        """
        SELECT
            d.drug_id,
            d.name,
            d.drugbank_id,
            d.original_indication,
            dr.vina_score,
            ml.ml_binding_score,
            ml.consensus_score,
            ml.consensus_rank,
            a.lipinski_pass,
            a.overall_pass,
            COALESCE(lit.lit_count, 0) AS lit_count
        FROM drugs d
        JOIN docking_results dr
            ON d.drug_id = dr.drug_id AND dr.pose_rank = 1
        JOIN (
            SELECT drug_id, target_id,
                   MIN(ml_binding_score) AS ml_binding_score,
                   MIN(consensus_score) AS consensus_score,
                   MIN(consensus_rank) AS consensus_rank
            FROM ml_scores
            GROUP BY drug_id, target_id
        ) ml ON d.drug_id = ml.drug_id AND dr.target_id = ml.target_id
        LEFT JOIN admet a
            ON d.drug_id = a.drug_id
        LEFT JOIN (
            SELECT drug_id, target_id, COUNT(*) AS lit_count
            FROM literature
            GROUP BY drug_id, target_id
        ) lit ON d.drug_id = lit.drug_id AND dr.target_id = lit.target_id
        WHERE dr.target_id = ?
        ORDER BY ml.consensus_rank
        """,
        (target_id,),
    )


def get_drug_details(drug_id: str) -> Optional[dict]:
    """Get full details for a single drug.

    Returns dict with drug properties, or None if not found.
    """
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM drugs WHERE drug_id = ?", (drug_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_drug_scores(drug_id: str) -> pd.DataFrame:
    """Get scores for a drug across ALL targets.

    Returns a DataFrame with columns: target_id, target_name, disease,
    vina_score, ml_binding_score, consensus_score, consensus_rank.
    """
    return _query_df(
        """
        SELECT
            t.target_id,
            t.name AS target_name,
            t.disease,
            dr.vina_score,
            ml.ml_binding_score,
            ml.consensus_score,
            ml.consensus_rank
        FROM targets t
        JOIN docking_results dr
            ON t.target_id = dr.target_id AND dr.pose_rank = 1
        JOIN ml_scores ml
            ON t.target_id = ml.target_id AND dr.drug_id = ml.drug_id
        WHERE dr.drug_id = ?
        ORDER BY t.disease, t.name
        """,
        (drug_id,),
    )


def get_drug_admet(drug_id: str) -> Optional[dict]:
    """Get ADMET profile for a single drug.

    Returns dict with ADMET properties, or None if not found.
    """
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM admet WHERE drug_id = ?", (drug_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_drug_literature(drug_id: str, target_id: Optional[str] = None) -> pd.DataFrame:
    """Get literature references for a drug, optionally filtered by target."""
    if target_id:
        return _query_df(
            """SELECT * FROM literature
               WHERE drug_id = ? AND target_id = ?
               ORDER BY confidence DESC""",
            (drug_id, target_id),
        )
    return _query_df(
        """SELECT * FROM literature
           WHERE drug_id = ?
           ORDER BY confidence DESC""",
        (drug_id,),
    )


def get_all_targets() -> pd.DataFrame:
    """Get all protein targets."""
    return _query_df("SELECT * FROM targets ORDER BY disease, name")


def get_interactions(
    drug_id: str, target_id: str, pose_rank: int = 1
) -> pd.DataFrame:
    """Get protein-ligand interactions for a specific docking pose.

    Returns DataFrame with columns: residue_name, residue_number, chain,
    interaction_type, distance.
    """
    return _query_df(
        """SELECT residue_name, residue_number, chain, interaction_type, distance
           FROM interactions
           WHERE drug_id = ? AND target_id = ? AND pose_rank = ?
           ORDER BY interaction_type, residue_number""",
        (drug_id, target_id, pose_rank),
    )


# ─── Export helpers for CSV downloads ─────────────────────────


def export_results_csv(target_id: str) -> pd.DataFrame:
    """Full results table for a target — suitable for CSV export."""
    return _query_df(
        """
        SELECT
            d.drug_id, d.name, d.drugbank_id, d.original_indication,
            d.smiles, d.molecular_weight, d.logp,
            dr.vina_score, ml.ml_binding_score,
            ml.consensus_score, ml.consensus_rank,
            a.lipinski_pass, a.hepatotoxicity_risk, a.herg_inhibition_risk,
            a.oral_bioavailability, a.overall_pass,
            COALESCE(lit.lit_count, 0) AS literature_count
        FROM drugs d
        JOIN docking_results dr ON d.drug_id = dr.drug_id AND dr.pose_rank = 1
        JOIN ml_scores ml ON d.drug_id = ml.drug_id AND dr.target_id = ml.target_id
        LEFT JOIN admet a ON d.drug_id = a.drug_id
        LEFT JOIN (
            SELECT drug_id, target_id, COUNT(*) AS lit_count
            FROM literature GROUP BY drug_id, target_id
        ) lit ON d.drug_id = lit.drug_id AND dr.target_id = lit.target_id
        WHERE dr.target_id = ?
        ORDER BY ml.consensus_rank
        """,
        (target_id,),
    )


def export_top_candidates(target_id: str, n: int = 10) -> pd.DataFrame:
    """Top N candidates for a target — ADMET-safe only."""
    df = export_results_csv(target_id)
    return df[df["overall_pass"] == 1].head(n)


def export_admet_csv() -> pd.DataFrame:
    """All ADMET profiles joined with drug names."""
    return _query_df(
        """
        SELECT d.drug_id, d.name, d.drugbank_id,
               a.lipinski_pass, a.hepatotoxicity_risk, a.herg_inhibition_risk,
               a.oral_bioavailability, a.overall_pass
        FROM admet a
        JOIN drugs d ON a.drug_id = d.drug_id
        ORDER BY d.name
        """
    )


def export_literature_csv() -> pd.DataFrame:
    """All literature evidence with drug and target names."""
    return _query_df(
        """
        SELECT l.drug_id, d.name AS drug_name, l.target_id,
               t.name AS target_name, t.disease,
               l.pmid, l.title, l.relationship, l.confidence
        FROM literature l
        JOIN drugs d ON l.drug_id = d.drug_id
        JOIN targets t ON l.target_id = t.target_id
        ORDER BY t.disease, d.name, l.confidence DESC
        """
    )
