# AI / LLM features

The literature feature calls a large language model through **your own API key**. The key
is read from an environment variable, is never committed, and never ships in the static
site. The dashboard works fully without it; it only enriches the literature evidence.

The offline **literature script** talks to any **OpenAI-compatible chat-completions
endpoint** (`LLM_API_KEY`, default model `gpt-4o-mini`), so it works with a hosted provider
or a local server unchanged.

The site previously had a runtime "Ask the data" chat assistant; it was removed on
2026-09-23 at the owner's request.

---

## 1. Literature relation extraction (offline, one-time)

Replaces the keyword-matched literature with a real read of each abstract: the model
judges whether a paper actually supports the drug-target link and returns a verdict,
relationship, confidence, and one-sentence rationale. This fixes the documented
weak-keyword limitation (e.g. an unrelated immunology paper no longer counts as
evidence).

```bash
export LLM_API_KEY=...                        # your key (required)
# optional:
export LLM_MODEL=gpt-4o-mini
export LLM_BASE_URL=https://api.openai.com    # any OpenAI-compatible endpoint
export NCBI_API_KEY=...                       # raises the PubMed fetch rate limit

python scripts/llm_literature.py --dry-run    # inspect one prompt, no LLM call, no key needed
python scripts/llm_literature.py --limit 5    # test your key cheaply (5 references)
python scripts/llm_literature.py              # process all (~130 refs, a few US cents)

python scripts/export_web_data.py             # merge results into web/public/data/literature.json
```

Output is cached in `data/literature_llm.json` (resumable; re-runs skip done refs).
Once merged, the Drug Explorer shows an "AI: <verdict>" line with the rationale on each
reference; before that it falls back to the keyword tier.
