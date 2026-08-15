#!/usr/bin/env python3
"""LLM-based literature relation extraction for GeneTropica.

Upgrades the keyword-mined literature evidence. For each drug-target PubMed
reference it fetches the abstract from NCBI and asks an LLM whether the paper
actually supports the drug acting on that target/disease, returning a verdict,
a short relationship label, a calibrated confidence, and a one-sentence note.

Results are cached to data/literature_llm.json (keyed by drug|target|pmid).
scripts/export_web_data.py merges that cache into web/public/data/literature.json
when it exists, so the dashboard shows "AI-reviewed" evidence where available and
falls back to the keyword view otherwise. Re-runs skip cached references, so it is
cheap and resumable.

You supply your own LLM key. It is read from the environment, never printed, and
never shipped in the static site.

Any OpenAI-compatible chat-completions endpoint works, so you can point it at a
hosted provider or a local server without changing the code.

Setup:
    export LLM_API_KEY=...                              # required to call the model
    export LLM_MODEL=gpt-4o-mini                        # optional; any chat model
    export LLM_BASE_URL=https://api.openai.com          # optional; any compatible endpoint
    export NCBI_API_KEY=...                             # optional; raises the PubMed rate limit

Usage:
    python scripts/llm_literature.py --dry-run     # fetch one abstract, print the prompt, no LLM call
    python scripts/llm_literature.py --limit 5     # process 5 references (test your key cheaply)
    python scripts/llm_literature.py               # process all uncached references
"""
import argparse
import json
import os
import re
import sqlite3
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "database" / "genetropica.db"
CACHE = ROOT / "data" / "literature_llm.json"

TARGET_CONTEXT = {
    "DENV_NS5": "dengue virus NS5 RNA-dependent RNA polymerase",
    "DENV_NS3": "dengue virus NS3 protease-helicase",
    "DENV_E": "dengue virus envelope (E) protein",
    "CHIKV_nsP2": "chikungunya virus nsP2 protease",
    "CHIKV_nsP1": "chikungunya virus nsP1 capping enzyme",
    "LEPTO_LipL32": "the Leptospira surface lipoprotein LipL32",
}


def fetch_abstract(pmid, ncbi_key=None):
    params = {"db": "pubmed", "id": pmid, "rettype": "abstract", "retmode": "text"}
    if ncbi_key:
        params["api_key"] = ncbi_key
    try:
        r = requests.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi", params=params, timeout=25)
        r.raise_for_status()
        return r.text.strip()
    except Exception as e:  # noqa: BLE001
        return f"(abstract unavailable: {e})"


def build_prompt(drug, target_ctx, title, abstract):
    return (
        "You are assessing biomedical literature for a drug-repurposing screen.\n"
        f"Drug: {drug}\n"
        f"Proposed target: {target_ctx}\n"
        f"Paper title: {title}\n\n"
        f"Abstract:\n{abstract[:6000]}\n\n"
        "Does this paper provide real evidence that the drug acts on (or is relevant to) that target "
        "or its disease? Be skeptical: many hits are keyword coincidences about unrelated topics.\n"
        'Respond with strict JSON only: {"verdict": one of "supports"|"related"|"unrelated"|"adverse", '
        '"relationship": a 2-4 word phrase, "confidence": a number 0.0-1.0, "note": one factual sentence}.'
    )


def _extract_json(text):
    """Models return prose-free JSON when asked, but tolerate stray fences or text."""
    m = re.search(r"\{.*\}", text.strip(), re.DOTALL)
    if not m:
        raise ValueError(f"no JSON object in model response: {text[:200]}")
    return json.loads(m.group(0))


def call_llm(prompt, key, base_url, model):
    r = requests.post(
        f"{base_url.rstrip('/')}/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "max_tokens": 400,
            "temperature": 0,
            "messages": [
                {
                    "role": "system",
                    "content": "You assess biomedical literature for a drug-repurposing screen. "
                    "Reply with a single strict JSON object and nothing else: no prose, no markdown fences.",
                },
                {"role": "user", "content": prompt},
            ],
        },
        timeout=90,
    )
    r.raise_for_status()
    text = r.json()["choices"][0]["message"].get("content", "") or ""
    return _extract_json(text)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="fetch one abstract and print the prompt; no LLM call")
    ap.add_argument("--limit", type=int, default=0, help="process at most N references")
    args = ap.parse_args()

    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    rows = con.execute(
        "SELECT d.name drug, l.target_id target, l.pmid, "
        "COALESCE(NULLIF(l.canonical_title,''), l.title) title "
        "FROM literature l JOIN drugs d ON d.drug_id=l.drug_id ORDER BY d.name, l.target_id"
    ).fetchall()

    cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    ncbi = os.environ.get("NCBI_API_KEY")
    key = os.environ.get("LLM_API_KEY")
    base = os.environ.get("LLM_BASE_URL", "https://api.openai.com")
    model = os.environ.get("LLM_MODEL", "gpt-4o-mini")

    if not args.dry_run and not key:
        sys.exit("Set LLM_API_KEY (or use --dry-run). The key is read from the environment and never stored.")

    todo = [r for r in rows if f"{r['drug']}|{r['target']}|{r['pmid']}" not in cache]
    if args.limit:
        todo = todo[: args.limit]
    print(f"{len(rows)} references total, {len(todo)} to process ({len(cache)} already cached); model={model}")

    for i, r in enumerate(todo, 1):
        ctx = TARGET_CONTEXT.get(r["target"], r["target"])
        abstract = fetch_abstract(r["pmid"], ncbi)
        prompt = build_prompt(r["drug"], ctx, r["title"], abstract)
        if args.dry_run:
            print("\n--- DRY RUN: prompt for one reference (no LLM call) ---\n")
            print(prompt[:1800])
            return
        ckey = f"{r['drug']}|{r['target']}|{r['pmid']}"
        try:
            out = call_llm(prompt, key, base, model)
        except Exception as e:  # noqa: BLE001
            print(f"  [{i}/{len(todo)}] {ckey} LLM error: {e}")
            continue
        cache[ckey] = {
            "verdict": str(out.get("verdict", "")).lower().strip(),
            "rel": str(out.get("relationship", "")).strip(),
            "conf": round(float(out.get("confidence", 0) or 0), 2),
            "note": str(out.get("note", "")).strip(),
        }
        print(f"  [{i}/{len(todo)}] {ckey} -> {cache[ckey]['verdict']} ({cache[ckey]['conf']})")
        CACHE.write_text(json.dumps(cache, indent=2))  # save as we go, so it is resumable
        time.sleep(0.4)

    if not args.dry_run:
        CACHE.write_text(json.dumps(cache, indent=2))
        print(f"Wrote {CACHE} ({len(cache)} entries). Re-run scripts/export_web_data.py to merge into literature.json.")


if __name__ == "__main__":
    main()
