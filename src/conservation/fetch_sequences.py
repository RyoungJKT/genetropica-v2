"""Fetch RdRp domain sequences from UniProt for evolutionary conservation analysis.

Downloads genome polyprotein sequences for 9 medically important viruses,
extracts the NS5 (or NS5B for HCV) RdRp domain, and saves FASTA files
for multiple sequence alignment.
"""

import logging
from pathlib import Path
from typing import Optional

import requests as http_requests

from src.utils.config import BASE_DIR

logger = logging.getLogger(__name__)

SEQUENCES_DIR: Path = BASE_DIR / "data" / "conservation" / "sequences"

UNIPROT_FASTA_URL = "https://rest.uniprot.org/uniprotkb/{uid}.fasta"

# RdRp domain sequences for 9 medically important viruses.
# NS5 boundaries extracted from UniProt feature annotations.
# For flaviviruses: extract NS5 chain (contains MTase + RdRp domains).
# For HCV: NS5B is already the standalone RdRp.
RDRP_SEQUENCES: dict = {
    "DENV-1": {
        "uniprot_id": "P33478",
        "name": "Dengue virus type 1",
        "protein": "NS5",
        "ns5_start": 2493,
        "ns5_end": 3391,
    },
    "DENV-2": {
        "uniprot_id": "P29990",
        "name": "Dengue virus type 2",
        "protein": "NS5",
        "ns5_start": 2492,
        "ns5_end": 3391,
    },
    "DENV-3": {
        "uniprot_id": "Q6YMS3",
        "name": "Dengue virus type 3",
        "protein": "NS5",
        "ns5_start": 2491,
        "ns5_end": 3390,
    },
    "DENV-4": {
        "uniprot_id": "Q2YHF0",
        "name": "Dengue virus type 4",
        "protein": "NS5",
        "ns5_start": 2488,
        "ns5_end": 3387,
    },
    "ZIKV": {
        "uniprot_id": "Q32ZE1",
        "name": "Zika virus",
        "protein": "NS5",
        "ns5_start": 2517,
        "ns5_end": 3419,
    },
    "YFV": {
        "uniprot_id": "P03314",
        "name": "Yellow fever virus",
        "protein": "NS5",
        "ns5_start": 2507,
        "ns5_end": 3411,
    },
    "WNV": {
        "uniprot_id": "P06935",
        "name": "West Nile virus",
        "protein": "NS5",
        "ns5_start": 2526,
        "ns5_end": 3430,
    },
    "JEV": {
        "uniprot_id": "P27395",
        "name": "Japanese encephalitis virus",
        "protein": "NS5",
        "ns5_start": 2528,
        "ns5_end": 3432,
    },
    "HCV": {
        "uniprot_id": "P26664",
        "name": "Hepatitis C virus",
        "protein": "NS5B",
        "ns5_start": 2421,
        "ns5_end": 3011,
    },
}


def parse_fasta(fasta_text: str) -> list[dict]:
    """Parse FASTA format text into list of {header, sequence} dicts.

    Args:
        fasta_text: Raw FASTA text with one or more sequences.

    Returns:
        List of dicts, each with 'header' and 'sequence' keys.
    """
    records: list[dict] = []
    current_header: Optional[str] = None
    current_seq_parts: list[str] = []

    for line in fasta_text.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith(">"):
            if current_header is not None:
                records.append({
                    "header": current_header,
                    "sequence": "".join(current_seq_parts),
                })
            current_header = line[1:]
            current_seq_parts = []
        else:
            current_seq_parts.append(line)

    if current_header is not None:
        records.append({
            "header": current_header,
            "sequence": "".join(current_seq_parts),
        })

    return records


def extract_ns5_domain(
    polyprotein_seq: str,
    ns5_start: int,
    ns5_end: int,
) -> str:
    """Extract NS5/NS5B domain from a polyprotein sequence.

    Args:
        polyprotein_seq: Full polyprotein amino acid sequence.
        ns5_start: 1-based start position of NS5 in polyprotein.
        ns5_end: 1-based end position of NS5 in polyprotein.

    Returns:
        NS5 domain sequence string.
    """
    return polyprotein_seq[ns5_start - 1 : ns5_end]


def fetch_sequence(uniprot_id: str, timeout: int = 15) -> Optional[str]:
    """Fetch a protein sequence from UniProt REST API.

    Args:
        uniprot_id: UniProt accession (e.g. 'P29990').
        timeout: HTTP request timeout in seconds.

    Returns:
        Full amino acid sequence string, or None on failure.
    """
    url = UNIPROT_FASTA_URL.format(uid=uniprot_id)
    try:
        resp = http_requests.get(url, timeout=timeout)
        resp.raise_for_status()
        records = parse_fasta(resp.text)
        if records:
            return records[0]["sequence"]
        return None
    except Exception as e:
        logger.warning("Failed to fetch %s: %s", uniprot_id, e)
        return None


def fetch_all_sequences(
    output_dir: Optional[Path] = None,
) -> dict[str, str]:
    """Fetch and extract NS5 RdRp domains for all 9 viruses.

    Downloads polyprotein from UniProt, extracts the NS5 domain,
    saves individual FASTA files and a combined multi-FASTA.

    Args:
        output_dir: Directory for output files. Defaults to SEQUENCES_DIR.

    Returns:
        Dict mapping virus short name to NS5 domain sequence.
    """
    out = output_dir or SEQUENCES_DIR
    out.mkdir(parents=True, exist_ok=True)

    sequences: dict[str, str] = {}

    for virus_name, info in RDRP_SEQUENCES.items():
        logger.info("Fetching %s (%s)...", virus_name, info["uniprot_id"])
        full_seq = fetch_sequence(info["uniprot_id"])

        if full_seq is None:
            logger.error("Failed to fetch %s — skipping", virus_name)
            continue

        ns5_seq = extract_ns5_domain(full_seq, info["ns5_start"], info["ns5_end"])
        sequences[virus_name] = ns5_seq

        # Save individual FASTA
        safe_name = virus_name.replace("-", "_").lower()
        fasta_path = out / f"{safe_name}_ns5.fasta"
        with open(fasta_path, "w") as f:
            f.write(
                f">{virus_name} | {info['name']} | {info['protein']}"
                f" | UniProt:{info['uniprot_id']}\n"
            )
            for i in range(0, len(ns5_seq), 80):
                f.write(ns5_seq[i : i + 80] + "\n")

        logger.info("  %s NS5: %d residues", virus_name, len(ns5_seq))

    # Save combined multi-FASTA
    if sequences:
        combined_path = out / "all_ns5.fasta"
        with open(combined_path, "w") as f:
            for virus_name, seq in sequences.items():
                info = RDRP_SEQUENCES[virus_name]
                f.write(f">{virus_name} | {info['name']} | {info['protein']}\n")
                for i in range(0, len(seq), 80):
                    f.write(seq[i : i + 80] + "\n")
        logger.info(
            "Combined multi-FASTA saved: %s (%d sequences)",
            combined_path,
            len(sequences),
        )

    return sequences
