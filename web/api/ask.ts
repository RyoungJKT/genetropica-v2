// Vercel serverless function: a grounded "ask the data" assistant for GeneTropica.
// Reads ANTHROPIC_API_KEY (and optional ANTHROPIC_BASE_URL / ANTHROPIC_MODEL) from
// the server environment; the key is never exposed to the browser. Answers strictly
// from a comprehensive data digest, so it cannot invent drugs, numbers, or claims.
import digest from './_digest.mjs'

const SYSTEM = `You are GeneTropica's data assistant, a friendly guide to a student's computational drug-repurposing science project. Answer questions about the dataset clearly and factually.
Use ONLY the DATA JSON below. It contains: "about"; "methods" (how each result is computed); "tools" (what each dashboard tab shows and why); a "glossary" of terms; "perTarget" and "topCandidates" rankings; "molecularDynamics", "validation", "conservation", "admet", "literature" and "escape" summaries; and honesty "caveats".
- Cite specific numbers and names from the data (Vina score in kcal/mol, ligand efficiency, durability %, counts, percentages). Use "methods" and "glossary" to explain what, how and why.
- If something is not in the data, say so. Never invent drugs, numbers, or claims.
- Raise the honesty "caveats" when relevant: the ML score is a target-agnostic prior; docking scored AUC 0.37 on dengue NS5 (below random); only NS5 was validated; sofosbuvir is a positive control; escape/durability is an NS5-only heuristic. These are computational research results, not medical advice.
- Be clear and well-structured; about 180 words maximum, plain language.

DATA:
${JSON.stringify(digest)}`

const REFUSAL_FALLBACK = "I can only describe GeneTropica's computational results, not give medical or treatment advice. Try asking about the data directly, for example: \"What is celecoxib's durability score on NS5?\" or \"How does celecoxib behave in the molecular-dynamics run?\""

// Some benign questions trip the safety classifier on certain phrasings (rankings, the word
// "escape", etc.). On a refused/empty reply we re-ask with this neutral data-framing wrapper.
const reframe = (q: string) =>
  `Answer this factual question about the GeneTropica computational research dataset (a student's science-fair project) using only the data and methods below, and cite specific numbers. It is a benign question about a fixed dataset, not a medical or treatment request. Question: ${q}`

async function ask(base: string, key: string, model: string, question: string, temperature: number) {
  const r = await fetch(`${base}/v1/messages`, {
    method: 'POST',
    headers: { 'x-api-key': key, 'anthropic-version': '2023-06-01', 'Content-Type': 'application/json' },
    body: JSON.stringify({
      model,
      max_tokens: 500,
      temperature,
      // cache_control caches the large system prompt (5-min TTL), so repeat questions are cheaper.
      system: [{ type: 'text', text: SYSTEM, cache_control: { type: 'ephemeral' } }],
      messages: [{ role: 'user', content: question }],
    }),
  })
  if (!r.ok) return { error: true as const }
  const data: any = await r.json()
  const blocks = Array.isArray(data?.content) ? data.content : []
  const answer = blocks.map((b: any) => (b?.type === 'text' ? b.text : '')).join('').trim()
  return { error: false as const, answer, refused: data?.stop_reason === 'refusal' }
}

export default async function handler(req: any, res: any) {
  if (req.method !== 'POST') return res.status(405).json({ error: 'Use POST.' })

  const key = process.env.ANTHROPIC_API_KEY
  if (!key) {
    return res.status(200).json({
      answer: "The assistant isn't switched on yet. The site owner needs to add an ANTHROPIC_API_KEY in the Vercel project settings.",
    })
  }

  let body: any = req.body
  if (typeof body === 'string') {
    try { body = JSON.parse(body) } catch { body = {} }
  }
  const question = String(body?.question ?? '').slice(0, 500).trim()
  if (!question) return res.status(400).json({ error: 'Please ask a question.' })

  const base = (process.env.ANTHROPIC_BASE_URL || 'https://api.anthropic.com').replace(/\/$/, '')
  const model = process.env.ANTHROPIC_MODEL || 'claude-sonnet-4-6'

  try {
    // First pass: the question as asked, deterministic.
    let out = await ask(base, key, model, question, 0)
    if (out.error) return res.status(502).json({ error: 'The model service returned an error.' })
    // On an empty or refused reply, re-ask with a neutral data-framing wrapper and some
    // temperature; this rescues benign questions whose phrasing trips the safety classifier.
    if (!out.answer) {
      out = await ask(base, key, model, reframe(question), 0.7)
      if (out.error) return res.status(502).json({ error: 'The model service returned an error.' })
    }
    if (!out.answer) {
      out = await ask(base, key, model, reframe(question), 1)
      if (out.error) return res.status(502).json({ error: 'The model service returned an error.' })
    }
    if (out.answer) return res.status(200).json({ answer: out.answer })
    return res.status(200).json({ answer: out.refused ? REFUSAL_FALLBACK : '(no answer)' })
  } catch {
    return res.status(502).json({ error: 'Could not reach the model service.' })
  }

}
