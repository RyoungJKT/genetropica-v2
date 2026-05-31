"""Recompute per-target candidate rankings using transparent, bias-aware metrics.

Docking-based virtual screening has well-documented scoring biases, and no
single number ranks candidates cleanly:

  * Raw AutoDock Vina score favours larger molecules (more atoms -> more
    contacts -> more negative score): a size bias.
  * Ligand efficiency (LE = -Vina / heavy_atom_count) corrects the size bias
    but over-rewards very small fragments.
  * The ligand-based ML model produces an identical score for a drug across
    all targets (it is a target-agnostic activity prior, not a per-target
    predictor).

Rather than collapse these into one misleading "consensus" rank, this script
ranks drug-like candidates (molecular weight 250-600 Da) by BOTH raw Vina and
ligand efficiency, stores both ranks, and keeps the ML score available only as
a clearly-labelled prior. The two ranks are complementary and are presented
side by side in the dashboard.

Run from the repo root:  python3 scripts/recompute_rankings.py
Idempotent: safe to re-run.
"""
import sqlite3
import sys
from pathlib import Path

try:
    from rdkit import Chem
except ImportError:
    sys.exit("RDKit is required: pip install rdkit (or use the conda env)")

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "database" / "genetropica.db"

# Drug-like molecular-weight band for candidate ranking. Removes the
# >600 Da molecules that dominate raw Vina by size, and the <250 Da
# fragments that dominate ligand efficiency by smallness.
DRUGLIKE_MW = (250.0, 600.0)


def _add_column(conn, table, column, coltype):
    """ADD COLUMN if it does not already exist (keeps the script idempotent)."""
    try:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {coltype}")
    except sqlite3.OperationalError as exc:
        if "duplicate column name" not in str(exc).lower():
            raise


def migrate_schema(conn):
    _add_column(conn, "drugs", "heavy_atoms", "INTEGER")
    _add_column(conn, "ml_scores", "ligand_efficiency", "REAL")
    _add_column(conn, "ml_scores", "vina_rank", "INTEGER")
    _add_column(conn, "ml_scores", "le_rank", "INTEGER")
    _add_column(conn, "ml_scores", "is_druglike", "INTEGER")
    conn.commit()


def populate_heavy_atoms(conn):
    """Compute heavy-atom count for each drug from its SMILES."""
    n = 0
    for drug_id, smiles in conn.execute(
        "SELECT drug_id, smiles FROM drugs WHERE smiles IS NOT NULL"
    ).fetchall():
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            continue
        conn.execute(
            "UPDATE drugs SET heavy_atoms = ? WHERE drug_id = ?",
            (mol.GetNumHeavyAtoms(), drug_id),
        )
        n += 1
    conn.commit()
    return n


def recompute_target(conn, target_id):
    """Compute LE, drug-like flag, and dual ranks for one target."""
    rows = conn.execute(
        """SELECT dr.drug_id,
                  MIN(dr.vina_score) AS best_vina,
                  d.molecular_weight AS mw,
                  d.heavy_atoms AS heavy
           FROM docking_results dr
           JOIN drugs d ON d.drug_id = dr.drug_id
           WHERE dr.target_id = ?
           GROUP BY dr.drug_id""",
        (target_id,),
    ).fetchall()

    recs = []
    for drug_id, best_vina, mw, heavy in rows:
        le = None
        druglike = 0
        if best_vina is not None and best_vina < 0 and heavy:
            le = -best_vina / heavy
        if mw is not None and DRUGLIKE_MW[0] <= mw <= DRUGLIKE_MW[1]:
            druglike = 1
        recs.append({
            "drug_id": drug_id, "vina": best_vina, "le": le,
            "druglike": druglike,
        })

    # Rank drug-like candidates only. Vina: most negative = rank 1.
    vina_pool = [r for r in recs if r["druglike"] and r["vina"] is not None and r["vina"] < 0]
    for rank, r in enumerate(sorted(vina_pool, key=lambda x: x["vina"]), start=1):
        r["vina_rank"] = rank
    # Ligand efficiency: highest = rank 1.
    le_pool = [r for r in recs if r["druglike"] and r["le"] is not None]
    for rank, r in enumerate(sorted(le_pool, key=lambda x: -x["le"]), start=1):
        r["le_rank"] = rank

    for r in recs:
        conn.execute(
            """UPDATE ml_scores
               SET ligand_efficiency = ?, is_druglike = ?,
                   vina_rank = ?, le_rank = ?
               WHERE drug_id = ? AND target_id = ?""",
            (round(r["le"], 4) if r["le"] is not None else None,
             r["druglike"],
             r.get("vina_rank"), r.get("le_rank"),
             r["drug_id"], target_id),
        )
    conn.commit()
    return len(recs), len(vina_pool)


def main():
    if not DB_PATH.exists():
        sys.exit(f"Database not found: {DB_PATH}")
    conn = sqlite3.connect(str(DB_PATH))
    try:
        migrate_schema(conn)
        n_heavy = populate_heavy_atoms(conn)
        print(f"Heavy-atom counts computed for {n_heavy} drugs.")
        targets = [r[0] for r in conn.execute(
            "SELECT DISTINCT target_id FROM ml_scores ORDER BY target_id"
        ).fetchall()]
        for t in targets:
            total, druglike = recompute_target(conn, t)
            print(f"  {t}: {total} drugs scored, {druglike} drug-like candidates ranked")
        print("Done. Rankings now use Vina + ligand efficiency over drug-like candidates.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
