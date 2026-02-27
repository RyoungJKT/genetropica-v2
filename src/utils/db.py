"""SQLite database operations for GeneTropica."""

import logging
import sqlite3
from pathlib import Path
from typing import Optional

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
    confidence REAL
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
