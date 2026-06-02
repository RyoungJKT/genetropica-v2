// Vercel serverless function: a grounded "ask the data" assistant for GeneTropica.
// Reads OPENAI_API_KEY (and optional LLM_BASE_URL / LLM_MODEL) from the server
// environment; the key is never exposed to the browser. Answers strictly from a
// compact data digest, so it cannot invent drugs, numbers, or claims.
import digest from './_digest.json'

const SYSTEM = `You are GeneTropica's data assistant for a computational drug-repurposing screen.
Answer the user's question using ONLY the DATA JSON below.
Rules:
- Use only facts present in the data and cite the specific numbers (Vina score in kcal/mol, ligand efficiency, counts).
- If the answer is not in the data, say you do not have that information. Never invent drugs, numbers, or claims.
- Keep the honesty caveats in mind and raise them when relevant (the ML score is a target-agnostic prior; docking scored AUC 0.37 on dengue NS5, below random; only NS5 was validated; sofosbuvir is a positive control, not a discovery).
- This is a research demonstration, not medical advice.
- Be concise: at most about 120 words, plain language.

DATA:
${JSON.stringify(digest)}`

export default async function handler(req: any, res: any) {
  if (req.method !== 'POST') return res.status(405).json({ error: 'Use POST.' })

  const key = process.env.OPENAI_API_KEY
  if (!key) {
    return res.status(200).json({
      answer: "The assistant isn't switched on yet. The site owner needs to add an OPENAI_API_KEY in the Vercel project settings.",
    })
  }

  let body: any = req.body
  if (typeof body === 'string') {
    try { body = JSON.parse(body) } catch { body = {} }
  }
  const question = String(body?.question ?? '').slice(0, 500).trim()
  if (!question) return res.status(400).json({ error: 'Please ask a question.' })

  const base = (process.env.LLM_BASE_URL || 'https://api.openai.com/v1').replace(/\/$/, '')
  const model = process.env.LLM_MODEL || 'gpt-4o-mini'

  try {
    const r = await fetch(`${base}/chat/completions`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${key}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({
        model,
        temperature: 0,
        max_tokens: 320,
        messages: [
          { role: 'system', content: SYSTEM },
          { role: 'user', content: question },
        ],
      }),
    })
    if (!r.ok) return res.status(502).json({ error: 'The model service returned an error.' })
    const data: any = await r.json()
    return res.status(200).json({ answer: data?.choices?.[0]?.message?.content ?? '(no answer)' })
  } catch {
    return res.status(502).json({ error: 'Could not reach the model service.' })
  }
}
