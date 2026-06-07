// Vercel serverless function: a grounded "ask the data" assistant for GeneTropica.
// Uses the Google Gemini API (generateContent). Reads GEMINI_API_KEY (and optional
// GEMINI_MODEL / GEMINI_BASE_URL) from the server environment; the key is never exposed
// to the browser. Answers strictly from a comprehensive data digest, so it cannot invent
// drugs, numbers, or claims. Safety thresholds are relaxed for this benign, grounded
// research dataset so legitimate "which candidate scores best" questions are not refused.
import digest from './_digest.mjs'

const SYSTEM = `You are GeneTropica's data assistant, a friendly guide to a student's computational drug-repurposing science project. Answer questions about the dataset clearly and factually.
Use ONLY the DATA JSON below. It contains: "about"; "methods" (how each result is computed); "tools" (what each dashboard tab shows and why); a "glossary" of terms; "perTarget" and "topCandidates" rankings; "molecularDynamics", "validation", "conservation", "admet", "literature" and "escape" summaries; and honesty "caveats".
- Cite specific numbers and names from the data (Vina score in kcal/mol, ligand efficiency, durability %, counts, percentages). Use "methods" and "glossary" to explain what, how and why.
- If something is not in the data, say so. Never invent drugs, numbers, or claims.
- Raise the honesty "caveats" when relevant: the ML score is a target-agnostic prior; docking scored AUC 0.37 on dengue NS5 (below random); only NS5 was validated; sofosbuvir is a positive control; escape/durability is an NS5-only heuristic. These are computational research results, not medical advice.
- Be clear and well-structured; about 180 words maximum, plain language.

DATA:
${JSON.stringify(digest)}`

const BLOCKED_FALLBACK = "I had trouble answering that one. Try asking about the data or methods directly, for example: \"How is the durability score on the Escape tab calculated?\", \"How does celecoxib behave in the molecular-dynamics run?\", or \"What are the top NS5 candidates by ligand efficiency?\" You can also browse the Candidates and Escape tabs."

// Relax the content filters: this is a grounded, benign research dataset, and the default
// thresholds wrongly block legitimate "which candidate scores best" type questions.
const SAFETY = ['HARM_CATEGORY_HARASSMENT', 'HARM_CATEGORY_HATE_SPEECH', 'HARM_CATEGORY_SEXUALLY_EXPLICIT', 'HARM_CATEGORY_DANGEROUS_CONTENT']
  .map((category) => ({ category, threshold: 'BLOCK_NONE' }))

async function ask(base: string, key: string, model: string, question: string, temperature: number) {
  const r = await fetch(`${base}/v1beta/models/${model}:generateContent`, {
    method: 'POST',
    headers: { 'x-goog-api-key': key, 'Content-Type': 'application/json' },
    body: JSON.stringify({
      systemInstruction: { parts: [{ text: SYSTEM }] },
      contents: [{ role: 'user', parts: [{ text: question }] }],
      generationConfig: { temperature, maxOutputTokens: 600 },
      safetySettings: SAFETY,
    }),
  })
  if (!r.ok) return { error: true as const }
  const data: any = await r.json()
  const cand = data?.candidates?.[0]
  const parts = cand?.content?.parts
  const answer = Array.isArray(parts) ? parts.map((p: any) => p?.text ?? '').join('').trim() : ''
  const blocked = cand?.finishReason === 'SAFETY' || !!data?.promptFeedback?.blockReason
  return { error: false as const, answer, blocked }
}

export default async function handler(req: any, res: any) {
  if (req.method !== 'POST') return res.status(405).json({ error: 'Use POST.' })

  const key = process.env.GEMINI_API_KEY
  if (!key) {
    return res.status(200).json({
      answer: "The assistant isn't switched on yet. The site owner needs to add a GEMINI_API_KEY in the Vercel project settings.",
    })
  }

  let body: any = req.body
  if (typeof body === 'string') {
    try { body = JSON.parse(body) } catch { body = {} }
  }
  const question = String(body?.question ?? '').slice(0, 500).trim()
  if (!question) return res.status(400).json({ error: 'Please ask a question.' })

  const base = (process.env.GEMINI_BASE_URL || 'https://generativelanguage.googleapis.com').replace(/\/$/, '')
  const model = process.env.GEMINI_MODEL || 'gemini-3.5-flash'

  try {
    let out = await ask(base, key, model, question, 0)
    if (out.error) return res.status(502).json({ error: 'The model service returned an error.' })
    if (!out.answer) {
      // The model occasionally returns an empty completion; retry once with a little temperature.
      out = await ask(base, key, model, question, 0.4)
      if (out.error) return res.status(502).json({ error: 'The model service returned an error.' })
    }
    return res.status(200).json({ answer: out.answer || (out.blocked ? BLOCKED_FALLBACK : '(no answer)') })
  } catch {
    return res.status(502).json({ error: 'Could not reach the model service.' })
  }
}
