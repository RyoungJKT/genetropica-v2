#!/usr/bin/env python3
"""Mock data generator for GeneTropica development.

Populates the SQLite database with realistic mock data including
FDA-approved drugs, protein targets, docking results, ML scores,
ADMET predictions, and literature evidence.
"""

import logging
import random
import sys
from pathlib import Path

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.utils.config import TARGET_PROTEINS
from src.utils.db import get_connection, init_db

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Seed for reproducibility
random.seed(42)

# --- Drug Data ---

DRUG_DATA = [
    ("metformin", "CC(=O)NC(=N)NC(=N)N", "Diabetes mellitus type 2", 129.16, -1.4),
    ("ibuprofen", "CC(C)Cc1ccc(cc1)C(C)C(=O)O", "Pain and inflammation", 206.28, 3.5),
    ("hydroxychloroquine", "CCN(CCO)CCCC(C)Nc1ccnc2cc(Cl)ccc12", "Malaria and lupus", 335.87, 3.6),
    ("chloroquine", "CCN(CC)CCCC(C)Nc1ccnc2cc(Cl)ccc12", "Malaria", 319.87, 4.6),
    ("doxycycline", "CC1C2C(O)C3C(=O)C(=C(O)C(N)=O)C(=O)C3(O)C(O)=C2C(=O)c2c(O)cccc21", "Bacterial infections", 444.43, -0.7),
    ("ivermectin", "CC(C)CC1OC2(CC3CC(C=CC(C)C(OC4CC(OC5CC(C)C(O)C(C)O5)C(O)C4OC)C(C)CC=CC=CC3OC2=O)C)O1", "Parasitic infections", 875.10, 4.1),
    ("ribavirin", "OCC1OC(n2cnc(C(=O)N)n2)C(O)C1O", "Hepatitis C", 244.20, -2.0),
    ("sofosbuvir", "CC(C)OC(=O)C(C)NP(=O)(OCC1OC(n2ccc(=O)[nH]c2=O)C(C(F)(F)F)C1O)Oc1ccccc1", "Hepatitis C", 529.45, 1.6),
    ("oseltamivir", "CCOC(=O)C1=CC(OC(CC)CC)C(NC(C)=O)C(N)C1", "Influenza", 312.40, 1.0),
    ("favipiravir", "NC1=NC(=O)C(=CN1)F", "Influenza and viral infections", 157.10, -0.6),
    ("remdesivir", "CCC(CC)COC(=O)C(C)NP(=O)(OCC1OC(n2cnc3c(N)ncnc32)C(O)C1O)Oc1ccccc1", "Antiviral (broad-spectrum)", 602.58, 1.9),
    ("lopinavir", "CC(C)C(NC(=O)C(CC1CCCCC1)CC(O)C(Cc1ccccc1)NC(=O)COc1c(C)cccc1C)C(=O)NC(CC(=O)N)C", "HIV protease inhibitor", 628.80, 5.9),
    ("ritonavir", "CC(C)C(NC(=O)OCC1CCCO1)C(=O)NC(CC(O)C(Cc1ccccc1)NC(=O)OCc1cncs1)CC1CCCCC1", "HIV protease inhibitor", 720.94, 5.2),
    ("celecoxib", "CC1=CC=C(C=C1)C1=CC(=NN1C1=CC=C(S(N)(=O)=O)C=C1)C(F)(F)F", "Pain and arthritis", 381.37, 3.5),
    ("amlodipine", "CCOC(=O)C1=C(COCCN)NC(C)=C(C1c1ccccc1Cl)C(=O)OC", "Hypertension", 408.88, 3.0),
    ("losartan", "CCCCc1nc(Cl)c(n1Cc1ccc(-c2ccccc2-c2nnn[nH]2)cc1)CO", "Hypertension", 422.91, 4.0),
    ("atorvastatin", "CC(C)c1n(CC(O)CC(O)CC(=O)O)c(c2ccc(F)cc2)c(c1c1ccccc1)C(=O)Nc1ccccc1", "Hyperlipidemia", 558.64, 4.1),
    ("methotrexate", "CN(Cc1cnc2nc(N)nc(N)c2n1)c1ccc(C(=O)NC(CCC(=O)O)C(=O)O)cc1", "Cancer and autoimmune", 454.44, -1.8),
    ("azithromycin", "CCC1OC(=O)C(C)C(OC2CC(C)(OC)C(O)C(C)O2)C(C)C(OC2OC(C)CC(N(C)C)C2O)C(C)(O)CC(C)C(=O)C(C)C(O)C1(C)O", "Bacterial infections", 748.98, 4.0),
    ("prednisone", "CC12CC(=O)C3C(CCC4=CC(=O)C=CC34C)C1CCC2(O)C(=O)CO", "Inflammation and autoimmune", 358.43, 1.5),
    ("dexamethasone", "CC1CC2C3CCC4=CC(=O)C=CC4(C)C3(F)C(O)CC2(C)C1(O)C(=O)CO", "Inflammation and edema", 392.46, 1.8),
    ("colchicine", "COc1cc2c(c(OC)c1OC)-c1ccc(OC)c(=O)cc1CC2NC(C)=O", "Gout", 399.44, 1.0),
    ("baricitinib", "CCS(=O)(=O)N1CC(CC1C#N)n1cc2c(n1)ncnc2N", "Rheumatoid arthritis", 371.42, 1.2),
    ("nitazoxanide", "CC(=O)Oc1ccc(NC(=O)c2ncc(s2)[N+](=O)[O-])cc1", "Parasitic diarrhea", 307.28, 2.3),
    ("suramin", "CC(=O)Nc1ccc2c(c1)cc(cc2S(=O)(=O)O)C(=O)Nc1ccc(cc1)C", "Trypanosomiasis", 1297.28, -2.0),
    ("praziquantel", "O=C1OC2CC3c4ccccc4CCN3CC2N1Cc1ccccc1", "Schistosomiasis", 312.41, 2.4),
    ("albendazole", "CCCSc1ccc2[nH]c(NC(=O)OC)nc2c1", "Helminth infections", 265.33, 2.7),
    ("mebendazole", "COC(=O)Nc1[nH]c2ccc(C(=O)c3ccccc3)cc2n1", "Worm infections", 295.29, 2.8),
    ("artemisinin", "CC1CCC2C(C)C(=O)OC3OC4(C)CCC1C23OO4", "Malaria", 282.33, 2.5),
    ("quinine", "COc1ccc2nccc(C(O)C3CC4CCN3CC4C=C)c2c1", "Malaria", 324.42, 3.4),
    ("primaquine", "COc1cc(N)c2ncccc2c1NC(C)CCCN", "Malaria (P. vivax)", 259.35, 2.1),
    ("dapsone", "Nc1ccc(cc1)S(=O)(=O)c1ccc(N)cc1", "Leprosy", 248.30, 0.97),
    ("rifampicin", "COC1C=COC2(C)Oc3c(C)c(O)c4c(c3C2=O)C(=O)C(NC(=O)C(C)=CC=CC(C)C(OC(C)=O)C(C)C(O)C(C)C(O)C(C)C=CC1C)=C(O)C4=O", "Tuberculosis", 822.94, 3.7),
    ("isoniazid", "NNC(=O)c1ccncc1", "Tuberculosis", 137.14, -0.7),
    ("pyrazinamide", "NC(=O)c1cnccn1", "Tuberculosis", 123.11, -0.6),
    ("ethambutol", "CCC(CO)NCCNC(CC)CO", "Tuberculosis", 204.31, -0.1),
    ("ciprofloxacin", "OC(=O)c1cn(C2CC2)c2cc(N3CCNCC3)c(F)cc2c1=O", "Bacterial infections", 331.34, 0.3),
    ("fluconazole", "OC(Cn1cncn1)(Cn1cncn1)c1ccc(F)cc1F", "Fungal infections", 306.27, 0.5),
    ("acyclovir", "NC1=Nc2c(ncn2COCCO)C(=O)N1", "Herpes simplex virus", 225.20, -1.6),
    ("zidovudine", "CC1=CN(C2CC(N=[N+]=[N-])C(CO)O2)C(=O)NC1=O", "HIV", 267.24, 0.1),
    ("tenofovir", "NC1=NC=NC2=C1N=CN2CCOP(=O)(O)O", "HIV and hepatitis B", 287.21, -1.6),
    ("entecavir", "NC1=NC(=O)C2=C(N1)N(C=N2)C1CC(CO)C(=C1)CO", "Hepatitis B", 277.28, -1.0),
    ("daclatasvir", "COC(=O)NC(C(=O)N1CCCC1c1ncc(-c2ccc(-c3ccn(C)c3)cc2)n1C)C1CCCCC1", "Hepatitis C", 738.88, 4.8),
    ("mycophenolate", "COc1c(C)c2COC(=O)c2c(O)c1CC=C(C)CCC(=O)OCCCCCCO", "Immunosuppressant", 433.49, 2.8),
    ("sirolimus", "COCC1CCC(=O)C(CC(OC(=O)C(C)CC2CCC(C)CC(OC3OC(C)CC(O)C3OC)C(=O)C(OC)CC(=O)CC(O)C1C)C1CCC(O)C(OC)C1)C=CC2OC", "Immunosuppressant", 914.17, 4.3),
    ("niclosamide", "Oc1ccc(Cl)cc1C(=O)Nc1ccc([N+](=O)[O-])cc1Cl", "Tapeworm infections", 327.12, 3.9),
    ("auranofin", "CCC(=O)OCC1OC(S[Au]PC)C(OC(=O)CC)C(OC(=O)CC)C1OC(=O)CC", "Rheumatoid arthritis", 678.48, 2.1),
    ("thalidomide", "O=C1CCC(N2C(=O)c3ccccc3C2=O)C(=O)N1", "Multiple myeloma", 258.23, 0.3),
    ("miltefosine", "CCCCCCCCCCCCCCCCOP(=O)([O-])OCC[N+](C)(C)C", "Leishmaniasis", 407.57, 5.5),
    ("benznidazole", "O=[N+]([O-])c1cn(CC(=O)NCc2ccccc2)cn1", "Chagas disease", 260.25, 0.8),
]


def _generate_drugs(conn) -> list[str]:
    """Insert 50 mock drugs and return their drug_ids."""
    drug_ids = []
    for i, (name, smiles, indication, mw, logp) in enumerate(DRUG_DATA):
        drug_id = f"DRUG_{i+1:04d}"
        drugbank_id = f"DB{i+1:05d}"
        conn.execute(
            """INSERT OR REPLACE INTO drugs
               (drug_id, name, drugbank_id, original_indication, smiles,
                molecular_weight, logp, pdbqt_path)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                drug_id,
                name,
                drugbank_id,
                indication,
                smiles,
                round(mw, 2),
                round(logp, 2),
                f"data/ligands/{name.replace(' ', '_')}.pdbqt",
            ),
        )
        drug_ids.append(drug_id)
    logger.info("Inserted %d drugs", len(drug_ids))
    return drug_ids


def _generate_targets(conn) -> list[str]:
    """Insert all 6 protein targets from config and return their target_ids."""
    target_ids = []
    for target_id, info in TARGET_PROTEINS.items():
        source = "experimental" if info["pdb_id"] in ("2VBC", "5CCV", "1OAN", "3TRK", "3FRH") else "predicted"
        conn.execute(
            """INSERT OR REPLACE INTO targets
               (target_id, name, disease, pdb_id, uniprot_id,
                structure_source, pdbqt_path)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                target_id,
                info["name"],
                info["disease"],
                info["pdb_id"],
                info["uniprot_id"],
                source,
                f"data/structures/{info['pdb_id']}.pdbqt",
            ),
        )
        target_ids.append(target_id)
    logger.info("Inserted %d targets", len(target_ids))
    return target_ids


def _generate_docking_results(
    conn, drug_ids: list[str], target_ids: list[str]
) -> dict[tuple[str, str], float]:
    """Generate docking results with 3 poses per drug-target pair.

    Returns a mapping of (drug_id, target_id) -> best vina score for
    downstream ML scoring.
    """
    # ~10% of drugs are designated "hits" with stronger binding scores
    hit_drugs = set(random.sample(drug_ids, k=max(1, len(drug_ids) // 10)))
    best_scores: dict[tuple[str, str], float] = {}
    count = 0

    for drug_id in drug_ids:
        for target_id in target_ids:
            is_hit = drug_id in hit_drugs
            # Hits get scores in -12.0 to -9.0 range; others in -8.5 to -3.0
            if is_hit:
                base_score = random.uniform(-12.0, -9.0)
            else:
                base_score = random.uniform(-8.5, -3.0)

            for pose_rank in range(1, 4):
                # Each subsequent pose is slightly worse
                pose_penalty = (pose_rank - 1) * random.uniform(0.3, 1.0)
                vina_score = round(base_score + pose_penalty, 2)
                conn.execute(
                    """INSERT OR REPLACE INTO docking_results
                       (drug_id, target_id, vina_score, pose_rank, pose_path)
                       VALUES (?, ?, ?, ?, ?)""",
                    (
                        drug_id,
                        target_id,
                        vina_score,
                        pose_rank,
                        f"data/docking_results/{drug_id}_{target_id}_pose{pose_rank}.pdbqt",
                    ),
                )
                count += 1

            best_scores[(drug_id, target_id)] = base_score

    logger.info("Inserted %d docking results (3 poses each)", count)
    return best_scores


def _normalize(value: float, min_val: float, max_val: float) -> float:
    """Min-max normalize a value to [0, 1] range."""
    if max_val == min_val:
        return 0.5
    return (value - min_val) / (max_val - min_val)


def _generate_ml_scores(
    conn,
    drug_ids: list[str],
    target_ids: list[str],
    best_vina: dict[tuple[str, str], float],
) -> None:
    """Generate ML rescoring with consensus rankings per target.

    Consensus score = 0.4 * normalized_vina + 0.6 * normalized_ml
    (Vina scores are negative, so more negative = better binding.)
    """
    # Collect all vina scores for normalization
    all_vina = list(best_vina.values())
    vina_min, vina_max = min(all_vina), max(all_vina)

    # First pass: compute raw ML and consensus scores
    raw_data: dict[str, list[tuple[str, float, float, float]]] = {
        tid: [] for tid in target_ids
    }

    for drug_id in drug_ids:
        for target_id in target_ids:
            vina_score = best_vina[(drug_id, target_id)]
            # ML score correlated with vina but with noise
            noise = random.gauss(0, 1.5)
            ml_binding_score = round(vina_score + noise, 3)

            # Normalize for consensus: invert so lower (more negative) = higher score
            norm_vina = 1.0 - _normalize(vina_score, vina_min, vina_max)
            ml_min, ml_max = vina_min - 3, vina_max + 3  # approximate ML range
            norm_ml = 1.0 - _normalize(ml_binding_score, ml_min, ml_max)

            consensus_score = round(0.4 * norm_vina + 0.6 * norm_ml, 4)
            raw_data[target_id].append(
                (drug_id, ml_binding_score, consensus_score, 0)
            )

    # Second pass: rank within each target and insert
    count = 0
    for target_id in target_ids:
        entries = raw_data[target_id]
        # Sort by consensus score descending (higher = better candidate)
        entries.sort(key=lambda x: x[2], reverse=True)
        for rank, (drug_id, ml_score, consensus, _) in enumerate(entries, start=1):
            conn.execute(
                """INSERT OR REPLACE INTO ml_scores
                   (drug_id, target_id, ml_binding_score, consensus_score,
                    consensus_rank)
                   VALUES (?, ?, ?, ?, ?)""",
                (drug_id, target_id, ml_score, consensus, rank),
            )
            count += 1

    logger.info("Inserted %d ML scores with consensus rankings", count)


def _generate_admet(conn, drug_ids: list[str]) -> None:
    """Generate ADMET predictions with realistic pass/fail distribution.

    ~80% pass Lipinski, ~15% hepatotoxicity risk, ~10% hERG risk.
    Overall pass requires all three criteria met.
    """
    count = 0
    for drug_id in drug_ids:
        lipinski_pass = random.random() < 0.80
        hepatotoxicity_risk = round(
            random.betavariate(1.5, 8) if random.random() > 0.15
            else random.uniform(0.5, 0.95),
            3,
        )
        herg_risk = round(
            random.betavariate(1.2, 10) if random.random() > 0.10
            else random.uniform(0.5, 0.90),
            3,
        )
        oral_bioavailability = round(random.uniform(0.2, 0.95), 3)

        overall_pass = (
            lipinski_pass
            and hepatotoxicity_risk < 0.5
            and herg_risk < 0.5
        )

        conn.execute(
            """INSERT OR REPLACE INTO admet
               (drug_id, lipinski_pass, hepatotoxicity_risk,
                herg_inhibition_risk, oral_bioavailability, overall_pass)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                drug_id,
                lipinski_pass,
                hepatotoxicity_risk,
                herg_risk,
                oral_bioavailability,
                overall_pass,
            ),
        )
        count += 1

    logger.info("Inserted %d ADMET profiles", count)


# Realistic PubMed-style article titles for literature evidence
_TITLE_TEMPLATES = [
    "In vitro antiviral activity of {drug} against {disease} virus",
    "Molecular docking analysis of {drug} with {target}: a computational study",
    "{drug} as a potential inhibitor of {disease} {target}: molecular dynamics simulation",
    "Repurposing {drug} for {disease}: binding affinity and selectivity profiling",
    "Structure-based virtual screening identifies {drug} as a {target} inhibitor",
    "Broad-spectrum antiviral effects of {drug} on {disease} and related flaviviruses",
    "Evaluation of {drug} for treatment of {disease} in a murine model",
    "Crystal structure of {target} in complex with {drug} reveals binding mechanism",
    "High-throughput screening of FDA-approved drugs against {disease} {target}",
    "Pharmacokinetic and efficacy assessment of {drug} for {disease} therapy",
]

_RELATIONSHIPS = [
    "inhibits viral replication",
    "binds active site",
    "reduces viral titer in vitro",
    "competitive inhibitor",
    "allosteric modulator",
    "blocks substrate binding",
    "synergistic with standard therapy",
    "disrupts protein-protein interaction",
]


def _generate_literature(
    conn, drug_ids: list[str], target_ids: list[str]
) -> None:
    """Generate mock literature evidence for ~30% of drug-target pairs."""
    count = 0
    for drug_id in drug_ids:
        for target_id in target_ids:
            if random.random() > 0.30:
                continue

            n_refs = random.randint(1, 3)
            target_info = TARGET_PROTEINS[target_id]

            for _ in range(n_refs):
                # Use the drug name from DRUG_DATA by parsing the drug index
                drug_idx = int(drug_id.split("_")[1]) - 1
                drug_name = DRUG_DATA[drug_idx][0]

                template = random.choice(_TITLE_TEMPLATES)
                title = template.format(
                    drug=drug_name.capitalize(),
                    disease=target_info["disease"],
                    target=target_info["name"],
                )
                pmid = str(random.randint(20000000, 39999999))
                relationship = random.choice(_RELATIONSHIPS)
                confidence = round(random.uniform(0.5, 0.95), 3)

                conn.execute(
                    """INSERT INTO literature
                       (drug_id, target_id, pmid, title, relationship, confidence)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (drug_id, target_id, pmid, title, relationship, confidence),
                )
                count += 1

    logger.info("Inserted %d literature entries", count)


def main() -> None:
    """Generate all mock data and populate the database."""
    logger.info("Initializing database...")
    init_db()

    conn = get_connection()
    try:
        drug_ids = _generate_drugs(conn)
        target_ids = _generate_targets(conn)
        best_vina = _generate_docking_results(conn, drug_ids, target_ids)
        _generate_ml_scores(conn, drug_ids, target_ids, best_vina)
        _generate_admet(conn, drug_ids)
        _generate_literature(conn, drug_ids, target_ids)
        conn.commit()
        logger.info("Mock data generation complete.")
    finally:
        conn.close()

    # Print summary
    conn = get_connection()
    try:
        print("\n--- Database Summary ---")
        for table in ["drugs", "targets", "docking_results", "ml_scores", "admet", "literature"]:
            count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            print(f"  {table}: {count} rows")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
