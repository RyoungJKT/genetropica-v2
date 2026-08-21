import { useState } from 'react'
import { useT } from '../i18n'

const SUGGESTIONS = [
  'Which drug-like candidates bind NS5 best?',
  'Is the ML score per-target?',
  'How rigorous and honest is the method?',
]

function Thinking() {
  const { t } = useT()
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 9 }}>
      <span style={{ display: 'inline-flex', gap: 5 }}>
        <span className="ask-dot" />
        <span className="ask-dot" style={{ animationDelay: '0.16s' }} />
        <span className="ask-dot" style={{ animationDelay: '0.32s' }} />
      </span>
      <span style={{ color: 'var(--ink-soft)', fontSize: 13 }}>{t('Reading the data')}</span>
    </div>
  )
}

export function AskAssistant() {
  const { t } = useT()
  const [open, setOpen] = useState(false)
  const [q, setQ] = useState('')
  const [answer, setAnswer] = useState('')
  const [err, setErr] = useState('')
  const [loading, setLoading] = useState(false)

  const ask = async (question: string) => {
    const text = question.trim()
    if (!text || loading) return
    setQ(text)
    setLoading(true)
    setErr('')
    setAnswer('')
    try {
      const r = await fetch('/api/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: text }),
      })
      const data = await r.json().catch(() => ({}))
      if (!r.ok) setErr(data?.error || t('Something went wrong.'))
      else setAnswer(data?.answer || t('(no answer)'))
    } catch {
      setErr(t('Could not reach the assistant. It runs on the deployed site, which needs the serverless function and an API key.'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <button
        onClick={() => setOpen((v) => !v)}
        aria-label={t('Ask the data')}
        style={{ position: 'fixed', right: 22, bottom: 22, zIndex: 80, fontFamily: 'var(--mono)', fontSize: 11, letterSpacing: '.08em', textTransform: 'uppercase', padding: '12px 18px', borderRadius: 100, border: '1px solid var(--ink)', background: 'var(--ink)', color: 'var(--paper)', cursor: 'pointer', boxShadow: '0 8px 24px rgba(28,26,23,.25)' }}
      >
        {open ? t('Close') : t('Ask the data')}
      </button>
      {open && (
        <div style={{ position: 'fixed', right: 22, bottom: 74, zIndex: 80, width: 'min(390px, 92vw)', background: 'var(--paper)', border: '2px solid var(--ink)', borderRadius: 16, boxShadow: '0 20px 54px rgba(28,26,23,.32)', padding: 18 }}>
          <div className="eyebrow" style={{ marginBottom: 6 }}>{t('Ask the data')}</div>
          <p style={{ fontSize: 12, color: 'var(--ink-faint)', lineHeight: 1.5, margin: '0 0 12px' }}>
            {t("Answers come only from this dashboard's data, with the same honesty caveats. A research demo, not medical advice.")}
          </p>
          <form onSubmit={(e) => { e.preventDefault(); ask(q) }} style={{ display: 'flex', gap: 8 }}>
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder={t('e.g. best NS5 binders?')}
              maxLength={500}
              style={{ flex: 1, fontFamily: 'var(--sans)', fontSize: 14, padding: '9px 12px', borderRadius: 10, border: '1px solid var(--line)', background: 'var(--paper-2)', color: 'var(--ink)' }}
            />
            <button type="submit" disabled={loading} style={{ fontFamily: 'var(--mono)', fontSize: 10.5, textTransform: 'uppercase', letterSpacing: '.06em', padding: '0 14px', borderRadius: 10, border: '1px solid var(--green)', background: 'var(--green)', color: 'var(--paper)', cursor: loading ? 'default' : 'pointer', opacity: loading ? 0.6 : 1 }}>
              {loading ? '...' : t('Ask')}
            </button>
          </form>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 10 }}>
            {SUGGESTIONS.map((s) => (
              <button key={s} onClick={() => ask(s)} style={{ fontSize: 11, color: 'var(--ink-soft)', background: 'var(--paper-2)', border: '1px solid var(--line)', borderRadius: 100, padding: '5px 10px', cursor: 'pointer', textAlign: 'left' }}>{t(s)}</button>
            ))}
          </div>
          {(answer || err || loading) && (
            <div style={{ marginTop: 14, fontSize: 13.5, lineHeight: 1.6, color: err ? 'var(--clay)' : 'var(--ink)', background: 'var(--paper-2)', border: '1px solid var(--line)', borderRadius: 10, padding: '12px 14px', maxHeight: 280, overflowY: 'auto', whiteSpace: 'pre-wrap' }}>
              {loading ? <Thinking /> : err || answer}
            </div>
          )}
        </div>
      )}
    </>
  )
}
