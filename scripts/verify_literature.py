#!/usr/bin/env python3
"""FIX-10: verify and tier the PubMed literature links.

For each stored PMID, calls NCBI E-utilities esummary to confirm the PMID
exists and to pull the canonical title, compares it to the stored title
(flagging mismatches), assigns an evidence tier, and records the fetch date.
Weak / keyword-only links are tiered as such so they can never inflate a
candidate's standing. Nothing is fabricated: unverifiable PMIDs are flagged,
not removed.

Run: python scripts/verify_literature.py
"""
import json
import re
import sqlite3
import urllib.parse
import urllib.request
from pathlib import Path

DB = Path(__file__).resolve().parents[1] / "data" / "database" / "genetropica.db"
FETCH_DATE = "2026-06-02"
EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
DISEASE = {"DENV": "dengue", "CHIKV": "chikungunya", "LEPTO": "leptospira"}
RELATED = ["zika", "west nile", "hepatitis c", "hcv", "sars", "cov", "japanese encephalitis",
           "yellow fever", "flavivir", "influenza"]


def norm(t):
    return re.sub(r"[^a-z0-9]", "", (t or "").lower())


def esummary(pmids):
    out = {}
    for i in range(0, len(pmids), 180):
        chunk = pmids[i:i + 180]
        url = f"{EUTILS}?db=pubmed&retmode=json&id=" + urllib.parse.quote(",".join(chunk))
        try:
            res = json.load(urllib.request.urlopen(url, timeout=40)).get("result", {})
            for uid in res.get("uids", []):
                rec = res.get(uid, {})
                if "error" not in rec:
                    out[uid] = rec.get("title", "")
        except Exception as e:  # noqa: BLE001
            print("  esummary error:", e)
    return out


def tier(rel, title, disease):
    t, rel = (title or "").lower(), (rel or "").lower()
    if any(k in t for k in ["in silico", "computational", "docking", "virtual screen", "molecular dynamics simulation"]):
        return "computational_only"
    if rel in ("unknown", "adverse", "pharmacokinetic"):
        return "weak_keyword"
    if rel in ("binds active site", "competitive inhibitor", "blocks substrate binding"):
        return "direct_target"
    if rel in ("inhibits viral replication", "reduces viral titer in vitro"):
        if disease and disease in t:
            return "same_pathogen_phenotypic"
        if any(k in t for k in RELATED):
            return "related_organism"
        return "same_pathogen_phenotypic"
    if rel == "mechanistic":
        return "mechanistic"
    return "weak_keyword"  # generic 'therapeutic' etc.


def main():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cols = [c[1] for c in cur.execute("PRAGMA table_info(literature)")]
    for col, typ in [("verified", "INTEGER"), ("title_match", "INTEGER"),
                     ("canonical_title", "TEXT"), ("evidence_tier", "TEXT"), ("verify_date", "TEXT")]:
        if col not in cols:
            cur.execute(f"ALTER TABLE literature ADD COLUMN {col} {typ}")

    rows = [dict(r) for r in cur.execute(
        "SELECT id, target_id, pmid, title, relationship FROM literature")]
    pmids = sorted({str(r["pmid"]) for r in rows})
    print(f"Verifying {len(pmids)} unique PMIDs across {len(rows)} links via NCBI esummary...")
    canon = esummary(pmids)
    print(f"  resolved {len(canon)}/{len(pmids)} PMIDs")

    mism, tiers = [], {}
    for r in rows:
        pmid = str(r["pmid"])
        ctitle = canon.get(pmid)
        exists = ctitle is not None
        tmatch = None
        if exists and r["title"]:
            ns, nc = norm(r["title"]), norm(ctitle)
            tmatch = int(ns[:45] in nc or nc[:45] in ns or ns == nc)
            if not tmatch:
                mism.append((pmid, r["title"][:45], ctitle[:45]))
        disease = DISEASE.get(r["target_id"].split("_")[0], "")
        ev = tier(r["relationship"], ctitle or r["title"], disease)
        tiers[ev] = tiers.get(ev, 0) + 1
        cur.execute(
            "UPDATE literature SET verified=?, title_match=?, canonical_title=?, evidence_tier=?, verify_date=? WHERE id=?",
            (int(exists), tmatch, ctitle, ev, FETCH_DATE, r["id"]),
        )
    con.commit()

    nver = cur.execute("SELECT COUNT(*) FROM literature WHERE verified=1").fetchone()[0]
    print(f"\nverified existing: {nver}/{len(rows)}")
    print(f"title mismatches (PMID resolves to a different paper than stored): {len(mism)}")
    for p, s, c in mism[:12]:
        print(f"   PMID {p}: stored '{s}...' vs NCBI '{c}...'")
    print("\nevidence tier distribution:")
    for k, v in sorted(tiers.items(), key=lambda x: -x[1]):
        print(f"   {k}: {v}")
    weak = cur.execute("SELECT COUNT(*) FROM literature WHERE evidence_tier IN ('weak_keyword','computational_only')").fetchone()[0]
    print(f"\nweak/keyword-only or computational-only (must not inflate rankings): {weak}")
    con.close()


if __name__ == "__main__":
    main()
