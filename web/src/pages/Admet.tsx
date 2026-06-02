import { useState } from 'react'
import { useAdmet, useDrugs } from '../data/api'
import { useRegister, say } from '../state/register'
import { bucketOf } from '../lib/buckets'
import type { Drug, AdmetRow } from '../data/types'

function band(v: number) {
  if (v < 0.3) return { label: 'low', color: 'var(--green)' }
  if (v < 0.6) return { label: 'medium', color: 'var(--gold)' }
  return { label: 'high', color: 'var(--clay)' }
}

const cellR = { padding: '9px 12px', textAlign: 'right' as const, fontFamily: 'var(--mono)', fontSize: 12, whiteSpace: 'nowrap' as const }

export default function Admet() {
  const admet = useAdmet()
  const drugs = useDrugs()
  const { reg } = useRegister()
  const [q, setQ] = useState('')
  const [passOnly, setPassOnly] = useState(false)
  const [hov, setHov] = useState<string | null>(null)

  const rows = (drugs.data ?? [])
    .map((d) => ({ drug: d, a: admet.data?.[d.name] }))
    .filter((r): r is { drug: Drug; a: AdmetRow } => !!r.a)
  const nPass = rows.filter((r) => r.a.pass).length
  const filtered = rows
    .filter((r) => (!q || r.drug.name.toLowerCase().includes(q.toLowerCase())) && (!passOnly || r.a.pass))
    .sort((x, y) => x.drug.name.localeCompare(y.drug.name))

  return (
    <div className="wrap" style={{ padding: '56px 0' }}>
      <div className="eyebrow">Tool 04</div>
      <h1 style={{ fontSize: 'clamp(34px,5vw,60px)', fontWeight: 380, marginTop: 12 }}>ADMET Profiling</h1>
      <p style={{ color: 'var(--ink-soft)', maxWidth: 720, lineHeight: 1.65, margin: '14px 0 6px' }}>
        {say(reg,
          'Whether each drug looks safe and drug-like: the Lipinski rule of five, predicted toxicity risks, and oral bioavailability. Risks are model estimates, not clinical results.',
          'Predicted ADMET per drug: Lipinski rule of five, hepatotoxicity and hERG risk scores (0 to 1), oral bioavailability, and an overall pass/flag. These are computational estimates, not experimental measurements.')}
      </p>
      {rows.length > 0 && (
        <p className="mono" style={{ color: 'var(--ink-faint)', marginBottom: 18 }}>{nPass} of {rows.length} pass the overall ADMET filter</p>
      )}

      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'center', marginBottom: 14 }}>
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search drug..." style={{ fontFamily: 'var(--sans)', fontSize: 14, padding: '8px 14px', borderRadius: 100, border: '1px solid var(--line)', background: 'var(--paper)', color: 'var(--ink)', minWidth: 180 }} />
        <button onClick={() => setPassOnly((v) => !v)} style={{ fontFamily: 'var(--mono)', fontSize: 10.5, letterSpacing: '.06em', textTransform: 'uppercase', padding: '8px 13px', borderRadius: 100, cursor: 'pointer', border: '1px solid var(--line)', background: passOnly ? 'var(--green)' : 'var(--paper)', color: passOnly ? 'var(--paper)' : 'var(--ink-soft)' }}>Passing only</button>
        <span className="mono" style={{ color: 'var(--ink-faint)' }}>{filtered.length} shown</span>
      </div>

      <div style={{ border: '1px solid var(--line)', borderRadius: 14, overflow: 'auto', maxHeight: 660, background: 'var(--paper)' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13.5 }}>
          <thead>
            <tr>
              {['Drug', 'Lipinski', 'Hepatotoxicity', 'hERG', 'Bioavailability', 'Overall'].map((h, i) => (
                <th key={h} style={{ position: 'sticky', top: 0, zIndex: 1, background: 'var(--paper-2)', padding: '10px 12px', textAlign: i === 0 ? 'left' : 'right', fontFamily: 'var(--mono)', fontSize: 10, letterSpacing: '.08em', textTransform: 'uppercase', color: 'var(--ink-faint)', borderBottom: '1px solid var(--line)', whiteSpace: 'nowrap' }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {filtered.map(({ drug, a }) => {
              const hb = band(a.hepatotox)
              const he = band(a.herg)
              return (
                <tr key={drug.name} onMouseEnter={() => setHov(drug.name)} onMouseLeave={() => setHov(null)} style={{ background: hov === drug.name ? 'var(--paper-2)' : 'transparent', borderBottom: '1px solid var(--line)' }}>
                  <td style={{ padding: '9px 12px' }}>
                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 9 }}>
                      <span style={{ width: 9, height: 9, borderRadius: '50%', background: bucketOf(drug).color, flex: 'none' }} />
                      <span style={{ textTransform: 'capitalize' }}>{drug.name.replace(/_/g, ' ')}</span>
                    </span>
                  </td>
                  <td style={{ ...cellR, color: a.lipinski ? 'var(--green)' : 'var(--clay)' }}>{a.lipinski ? 'pass' : 'fail'}</td>
                  <td style={{ ...cellR, color: hb.color }}>{hb.label} ({a.hepatotox.toFixed(2)})</td>
                  <td style={{ ...cellR, color: he.color }}>{he.label} ({a.herg.toFixed(2)})</td>
                  <td style={{ ...cellR, color: 'var(--ink-soft)' }}>{Math.round(a.bioavail * 100)}%</td>
                  <td style={{ ...cellR, color: a.pass ? 'var(--green)' : 'var(--clay)' }}>{a.pass ? 'pass' : 'flag'}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
