# AI / LLM features

Both features call a large language model through **your own API key**. The key is
read from an environment variable, is never committed, and never ships in the static
site. The dashboard works fully without them; these only enrich it.

Provider-agnostic: anything with an OpenAI-compatible `/chat/completions` endpoint
works (OpenAI, Together, Groq, a local server, ...). Defaults to OpenAI `gpt-4o-mini`.

---

## 1. Literature relation extraction (offline, one-time)

Replaces the keyword-matched literature with a real read of each abstract: the model
judges whether a paper actually supports the drug-target link and returns a verdict,
relationship, confidence, and one-sentence rationale. This fixes the documented
weak-keyword limitation (e.g. an unrelated immunology paper no longer counts as
evidence).

```bash
export OPENAI_API_KEY=sk-...                 # your key (required)
# optional:
export LLM_BASE_URL=https://api.openai.com/v1
export LLM_MODEL=gpt-4o-mini
export NCBI_API_KEY=...                       # raises the PubMed fetch rate limit

python scripts/llm_literature.py --dry-run    # inspect one prompt, no LLM call, no key needed
python scripts/llm_literature.py --limit 5    # test your key cheaply (5 references)
python scripts/llm_literature.py              # process all (~130 refs, a few US cents)

python scripts/export_web_data.py             # merge results into web/public/data/literature.json
```

Output is cached in `data/literature_llm.json` (resumable; re-runs skip done refs).
Once merged, the Drug Explorer shows an "AI: <verdict>" line with the rationale on each
reference; before that it falls back to the keyword tier.

---

## 2. Ask-the-data assistant (runtime)

A grounded natural-language Q&A over the dashboard's own data, via a Vercel serverless
function. (Setup added when the feature is built.)

> Note: the endpoint is public, so each question spends your credits. It is built with
> token caps and a light rate limit; for a public site consider gating it or watching usage.
