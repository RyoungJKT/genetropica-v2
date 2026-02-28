"""PubMedBERT NLP pipeline for literature evidence mining.

Searches PubMed via NCBI E-utilities API for existing evidence
linking drug candidates to disease targets. Uses keyword-based
relationship extraction with optional PubMedBERT upgrade.
"""

import logging
import re
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional

import requests

from src.utils.config import TARGET_PROTEINS
from src.utils.db import get_connection

logger = logging.getLogger(__name__)

_ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
_EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

# Drug synonyms: generic name → list of alternative search terms
# Includes brand names, metabolite names, and common abbreviations
DRUG_SYNONYMS: dict[str, list[str]] = {
    "sofosbuvir": ["Sovaldi", "GS-7977", "GS-461203", "PSI-7977"],
    "remdesivir": ["Veklury", "GS-5734", "GS-441524"],
    "favipiravir": ["Avigan", "T-705"],
    "ribavirin": ["Virazole", "Copegus", "Rebetol"],
    "oseltamivir": ["Tamiflu"],
    "lopinavir": ["Kaletra"],
    "ritonavir": ["Norvir"],
    "hydroxychloroquine": ["Plaquenil", "HCQ"],
    "chloroquine": ["Aralen", "CQ"],
    "ivermectin": ["Stromectol", "Mectizan"],
    "doxycycline": ["Vibramycin"],
    "azithromycin": ["Zithromax", "Z-pack"],
    "niclosamide": ["Niclocide", "Yomesan"],
    "baricitinib": ["Olumiant"],
    "daclatasvir": ["Daklinza", "BMS-790052"],
    "acyclovir": ["Zovirax"],
    "entecavir": ["Baraclude"],
    "tenofovir": ["Viread", "TDF", "tenofovir disoproxil"],
    "mycophenolate": ["CellCept", "mycophenolic acid", "MPA"],
    "sirolimus": ["rapamycin", "Rapamune"],
    "celecoxib": ["Celebrex"],
    "dexamethasone": ["Decadron"],
    "miltefosine": ["Impavido"],
    "nitazoxanide": ["Alinia"],
}

# Target name synonyms: config target name → list of alternative search terms
TARGET_SYNONYMS: dict[str, list[str]] = {
    "NS3 Protease-Helicase": ["NS3", "DENV NS3", "dengue NS3 protease", "NS3pro"],
    "NS5 RNA-dependent RNA Polymerase": [
        "NS5 RdRp", "DENV NS5", "dengue NS5", "dengue polymerase",
        "dengue RNA polymerase", "NS5 polymerase", "flavivirus RdRp",
    ],
    "Envelope (E) Protein": ["DENV E protein", "dengue envelope", "dengue E glycoprotein"],
    "nsP2 Protease": ["CHIKV nsP2", "chikungunya nsP2", "nsP2 cysteine protease"],
    "nsP1 Capping Enzyme": ["CHIKV nsP1", "chikungunya nsP1", "nsP1 methyltransferase"],
    "LipL32": ["leptospiral LipL32", "LipL32 lipoprotein", "Leptospira LipL32"],
}

# Relationship keywords for classification
_RELATIONSHIP_PATTERNS = {
    "therapeutic": [
        r"\b(?:treat|therap|inhibit|antiviral|antibacterial|antimicrobial)\w*\b",
        r"\b(?:efficac|potent|active against|suppress)\w*\b",
    ],
    "mechanistic": [
        r"\b(?:bind|interact|dock|affinity|substrate|catalytic)\w*\b",
        r"\b(?:mechanism|pathway|signal|cascade|receptor)\w*\b",
    ],
    "adverse": [
        r"\b(?:toxic|adverse|side.effect|contraindic|hepatotox)\w*\b",
        r"\b(?:cardiotox|nephrotox|risk|danger|harm)\w*\b",
    ],
    "pharmacokinetic": [
        r"\b(?:absorb|distribut|metaboli|excret|bioavailab)\w*\b",
        r"\b(?:clearance|half.life|plasma|concentration|pharmacokinet)\w*\b",
    ],
}


def search_pubmed(query: str, max_results: int = 50) -> list[dict]:
    """Search PubMed via NCBI E-utilities API.

    Args:
        query: Search query string.
        max_results: Maximum number of results to return.

    Returns:
        List of dicts with 'pmid', 'title', and 'abstract'.
    """
    # Step 1: ESearch to get PMIDs
    try:
        resp = requests.get(
            _ESEARCH_URL,
            params={
                "db": "pubmed",
                "term": query,
                "retmax": max_results,
                "retmode": "json",
                "sort": "relevance",
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        pmids = data.get("esearchresult", {}).get("idlist", [])
    except requests.RequestException as e:
        logger.warning("PubMed search failed: %s", e)
        return []

    if not pmids:
        return []

    # Step 2: EFetch to get article details
    time.sleep(0.35)  # Respect NCBI rate limits

    try:
        resp = requests.get(
            _EFETCH_URL,
            params={
                "db": "pubmed",
                "id": ",".join(pmids),
                "rettype": "xml",
                "retmode": "xml",
            },
            timeout=30,
        )
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.warning("PubMed fetch failed: %s", e)
        return []

    return _parse_pubmed_xml(resp.text)


def _parse_pubmed_xml(xml_text: str) -> list[dict]:
    """Parse PubMed XML response into article dicts."""
    articles = []

    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        logger.warning("Failed to parse PubMed XML: %s", e)
        return []

    for article in root.findall(".//PubmedArticle"):
        pmid_el = article.find(".//PMID")
        title_el = article.find(".//ArticleTitle")
        abstract_el = article.find(".//AbstractText")

        pmid = pmid_el.text if pmid_el is not None else ""
        title = title_el.text if title_el is not None else ""
        abstract = abstract_el.text if abstract_el is not None else ""

        if pmid and title:
            articles.append({
                "pmid": pmid,
                "title": title,
                "abstract": abstract or "",
            })

    return articles


def extract_relationships(abstract_text: str) -> list[dict]:
    """Extract drug-target relationship types from abstract text.

    Uses regex-based keyword matching for classification. Returns
    all detected relationship types with confidence scores.

    Args:
        abstract_text: Full abstract text.

    Returns:
        List of dicts with 'relationship' and 'confidence'.
    """
    if not abstract_text:
        return []

    text_lower = abstract_text.lower()
    results = []

    for rel_type, patterns in _RELATIONSHIP_PATTERNS.items():
        match_count = 0
        for pattern in patterns:
            matches = re.findall(pattern, text_lower)
            match_count += len(matches)

        if match_count > 0:
            # Confidence based on number of keyword matches
            confidence = min(0.3 + match_count * 0.1, 0.95)
            results.append({
                "relationship": rel_type,
                "confidence": round(confidence, 2),
            })

    # Sort by confidence descending
    results.sort(key=lambda x: x["confidence"], reverse=True)
    return results


def mine_target(target_name: str, disease: str, max_results: int = 20) -> list[dict]:
    """Find relevant literature for a protein target.

    Args:
        target_name: Protein target name (e.g. 'NS3 Protease').
        disease: Disease name (e.g. 'Dengue').
        max_results: Maximum papers to retrieve.

    Returns:
        List of article dicts with relationship annotations.
    """
    query = f"{target_name} {disease} drug"
    articles = search_pubmed(query, max_results=max_results)

    for article in articles:
        rels = extract_relationships(article.get("abstract", ""))
        article["relationships"] = rels

    logger.info("Mined %d articles for %s / %s", len(articles), target_name, disease)
    return articles


def _build_synonym_query(
    drug_name: str, target_name: str, disease: str,
) -> str:
    """Build a PubMed query with drug and target synonyms for broader recall.

    Uses Boolean OR to include alternative names, and AND to combine
    the drug term, target term, and disease.

    Args:
        drug_name: Primary drug name.
        target_name: Primary target name.
        disease: Disease name.

    Returns:
        PubMed query string with synonym expansion.
    """
    # Drug terms: generic name + any known synonyms
    drug_lower = drug_name.lower()
    drug_terms = [drug_name]
    if drug_lower in DRUG_SYNONYMS:
        drug_terms.extend(DRUG_SYNONYMS[drug_lower])
    drug_clause = " OR ".join(f'"{t}"' for t in drug_terms)

    # Target terms: full name + abbreviations
    target_terms = [target_name]
    if target_name in TARGET_SYNONYMS:
        target_terms.extend(TARGET_SYNONYMS[target_name])
    target_clause = " OR ".join(f'"{t}"' for t in target_terms)

    return f"({drug_clause}) AND ({target_clause}) AND {disease}"


def mine_drug_target(
    drug_name: str, target_name: str, disease: str, max_results: int = 10,
) -> list[dict]:
    """Check if a specific drug-target relationship exists in PubMed.

    Uses synonym expansion for both drug names (brand names, metabolite
    codes) and target names (abbreviations, common aliases) to maximize
    recall of relevant literature.

    Args:
        drug_name: Drug name (e.g. 'Sofosbuvir').
        target_name: Target name (e.g. 'NS5 RdRp').
        disease: Disease name (e.g. 'Dengue').
        max_results: Maximum papers to retrieve.

    Returns:
        List of relevant articles with relationships.
    """
    query = _build_synonym_query(drug_name, target_name, disease)
    articles = search_pubmed(query, max_results=max_results)

    for article in articles:
        rels = extract_relationships(article.get("abstract", ""))
        article["relationships"] = rels

    return articles


def batch_mine(
    db_path: Optional[Path] = None,
    max_per_pair: int = 5,
) -> int:
    """Run literature mining for all drug-target pairs with docking scores.

    Queries PubMed for each drug-target combination and stores
    results in the literature table.

    Args:
        db_path: Optional database path override.
        max_per_pair: Maximum articles per drug-target pair.

    Returns:
        Total number of literature entries stored.
    """
    conn = get_connection(db_path)
    total = 0

    try:
        # Get all drug-target pairs with docking results
        pairs = conn.execute(
            """SELECT DISTINCT d.drug_id, d.name AS drug_name,
                      dr.target_id, t.name AS target_name, t.disease
               FROM drugs d
               JOIN docking_results dr ON d.drug_id = dr.drug_id
               JOIN targets t ON dr.target_id = t.target_id
               WHERE dr.pose_rank = 1
               ORDER BY d.drug_id, dr.target_id"""
        ).fetchall()

        for pair in pairs:
            drug_id = pair["drug_id"]
            drug_name = pair["drug_name"]
            target_id = pair["target_id"]
            target_name = pair["target_name"]
            disease = pair["disease"]

            articles = mine_drug_target(
                drug_name, target_name, disease,
                max_results=max_per_pair,
            )

            for article in articles:
                rels = article.get("relationships", [])
                rel_type = rels[0]["relationship"] if rels else "unknown"
                confidence = rels[0]["confidence"] if rels else 0.3

                conn.execute(
                    """INSERT OR IGNORE INTO literature
                       (drug_id, target_id, pmid, title, relationship, confidence)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (drug_id, target_id, article["pmid"],
                     article["title"], rel_type, confidence),
                )
                total += 1

            # Rate limit: be kind to NCBI
            time.sleep(0.4)

        conn.commit()
        logger.info("Literature mining complete: %d entries stored", total)

    finally:
        conn.close()

    return total
