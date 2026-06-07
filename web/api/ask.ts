// Vercel serverless function: a grounded "ask the data" assistant for GeneTropica.
// Reads LLM_API_KEY (and optional LLM_BASE_URL / LLM_MODEL) from
// the server environment; the key is never exposed to the browser. Answers strictly
// from a comprehensive data digest, so it cannot invent drugs, numbers, or claims.
import digest from './_digest.mjs'

const SYSTEM = `You are GeneTropica's data assistant for a computational drug-repurposing screen.
Answer using ONLY the DATA JSON below. It contains: "about" (overview); "methods" (HOW each result is computed); "tools" (WHAT each dashboard tab shows and WHY); a "glossary" of terms; "perTarget" and "topCandidates" rankings; "molecularDynamics", "validation", "conservation", "admet", "literature" and "escape" summaries; and honesty "caveats".
Rules:
- Use only facts present in the data. Cite specific numbers and names (Vina kcal/mol, ligand efficiency, counts, percentages). Use "methods" and "glossary" to explain what, how and why.
- If something is not in the data, say so plainly. Never invent drugs, numbers, or claims.
- Always respect the honesty caveats and raise them when relevant (the ML score is a target-agnostic prior; docking scored AUC 0.37 on dengue NS5, below random; only NS5 was validated; sofosbuvir is a positive control, not a discovery; escape/durability is an NS5-only heuristic).
- This is a research demonstration, not medical advice.
- Be clear and well-structured; about 180 words maximum, plain language.

DATA:
${JSON.stringify(digest)}`

async function ask(base: string, key: string, model: string, question: string, temperature: number) {
  const r = await fetch(`${base}/v1/messages`, {
    method: 'POST',
    headers: { 'x-api-key': key, 'x-api-version': '2023-06-01', 'Content-Type': 'application/json' },
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
  const answer = Array.isArray(data?.content)
    ? data.content.map((b: any) => (b?.type === 'text' ? b.text : '')).join('').trim()
    : ''
  return { error: false as const, answer }
}

export default async function handler(req: any, res: any) {
  if (req.method !== 'POST') return res.status(405).json({ error: 'Use POST.' })

  const key = process.env.LLM_API_KEY
  if (!key) {
    return res.status(200).json({
      answer: "The assistant isn't switched on yet. The site owner needs to add an LLM_API_KEY in the Vercel project settings.",
    })
  }

  let body: any = req.body
  if (typeof body === 'string') {
    try { body = JSON.parse(body) } catch { body = {} }
  }
  const question = String(body?.question ?? '').slice(0, 500).trim()
  if (!question) return res.status(400).json({ error: 'Please ask a question.' })

  const base = (process.env.LLM_BASE_URL || 'https://api.openai.com').replace(/\/$/, '')
  const model = process.env.LLM_MODEL || 'default-model'

  try {
    let out = await ask(base, key, model, question, 0)
    if (out.error) return res.status(502).json({ error: 'The model service returned an error.' })
    if (!out.answer) {
      // The model occasionally returns an empty completion; retry once with a little temperature.
      out = await ask(base, key, model, question, 0.4)
      if (out.error) return res.status(502).json({ error: 'The model service returned an error.' })
    }
    return res.status(200).json({ answer: out.answer || '(no answer)' })
  } catch {
    return res.status(502).json({ error: 'Could not reach the model service.' })
  }
}
