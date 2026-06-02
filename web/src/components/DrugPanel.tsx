import { useRef, useEffect } from 'react'
import type { Drug, Field, AdmetRow } from '../data/types'
import { RadarChart } from './RadarChart'

function Meta({ k, v }: { k: string; v: string }) {
  return (
    <div>
      <div style={{ fontFamily: 'var(--mono)', fontSize: 10, letterSpacing: '.08em', textTransform: 'uppercase', color: 'var(--ink-faint)' }}>{k}</div>
      <div style={{ fontSize: 15, color: 'var(--ink)', marginTop: 3, overflowWrap: 'anywhere' }}>{v}</div>
    </div>
  )
}

/** Inline per-drug detail: metadata, cross-target binding bars (Vina + the constant ML prior), ADMET radar. */
export function DrugPanel({ drug, field, admet, order, tName }: { drug: Drug; field: Field; admet?: AdmetRow; order: string[]; tName: (id: string) => string }) {
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => {
    ref.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  }, [drug.name])

  const bars = order.map((tid) => {
    const p = (field[tid] ?? []).find((x) => x.name === drug.name)
    return { tid, name: tName(tid), vina: p ? Math.abs(p.vina) : 0, raw: p ? p.vina : null }
  })
  const ml = drug.ml ?? 0
  const xMax = Math.max(10, ...bars.map((b) => b.vina), ml)
  const ticks = [0, 2, 4, 6, 8, 10].filter((t) => t <= xMax)

  const radarAxes = admet
    ? [
        { label: 'Lipinski Compliance', value: admet.lipinski },
        { label: 'Oral Bioavailability', value: admet.bioavail },
        { label: 'Overall Safety', value: admet.pass },
        { label: 'hERG Safety', value: 1 - admet.herg },
        { label: 'Hepato Safety', value: 1 - admet.hepatotox },
      ]
    : []

  return (
    <section ref={ref} style={{ marginTop: 36, scrollMarginTop: 80 }}>
      <h2 style={{ fontSize: 32, textTransform: 'capitalize', fontWeight: 380 }}>{drug.name.replace(/_/g, ' ')}</h2>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: 18, marginTop: 16 }}>
        <Meta k="DrugBank ID" v={drug.drugbank_id ?? 'None'} />
        <Meta k="Indication" v={drug.indication ?? '-'} />
        <Meta k="Molecular Weight" v={`${Math.round(drug.molecular_weight)} Da`} />
        <Meta k="LogP" v={drug.logp != null ? drug.logp.toFixed(2) : '-'} />
      </div>
      {drug.smiles && (
        <div style={{ marginTop: 16 }}>
          <div style={{ fontFamily: 'var(--mono)', fontSize: 10, letterSpacing: '.08em', textTransform: 'uppercase', color: 'var(--ink-faint)', marginBottom: 4 }}>SMILES</div>
          <div style={{ fontFamily: 'var(--mono)', fontSize: 12.5, color: 'var(--ink)', background: 'var(--paper-2)', border: '1px solid var(--line)', borderRadius: 10, padding: '10px 12px', overflowX: 'auto', whiteSpace: 'nowrap' }}>{drug.smiles}</div>
        </div>
      )}

      <hr style={{ border: 0, borderTop: '1px solid var(--line)', margin: '28px 0' }} />

      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1.15fr) minmax(0, 1fr)', gap: 32, alignItems: 'start' }}>
        <div>
          <h3 style={{ fontSize: 15, marginBottom: 4 }}>Binding Scores Across Targets</h3>
          <div style={{ display: 'flex', gap: 16, margin: '6px 0 14px', fontSize: 11, fontFamily: 'var(--mono)', color: 'var(--ink-soft)' }}>
            <span><span style={{ display: 'inline-block', width: 10, height: 10, background: 'var(--green)', borderRadius: 2, marginRight: 6, verticalAlign: 'middle' }} />Vina |score|</span>
            <span><span style={{ display: 'inline-block', width: 10, height: 10, background: 'var(--gold)', borderRadius: 2, marginRight: 6, verticalAlign: 'middle' }} />ML |score|</span>
          </div>
          {bars.map((b) => (
            <div key={b.tid} style={{ display: 'grid', gridTemplateColumns: '168px 1fr', gap: 10, alignItems: 'center', margin: '9px 0' }}>
              <span style={{ fontSize: 11.5, color: 'var(--ink-soft)', textAlign: 'right', lineHeight: 1.2 }}>{b.name}</span>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, height: 9 }}>
                  <div style={{ width: `${(ml / xMax) * 100}%`, height: 7, background: 'var(--gold)', borderRadius: 2, minWidth: ml > 0 ? 2 : 0 }} />
                  <span style={{ fontFamily: 'var(--mono)', fontSize: 9.5, color: 'var(--ink-faint)' }}>{ml.toFixed(2)}</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, height: 13, marginTop: 2 }}>
                  <div style={{ width: `${(b.vina / xMax) * 100}%`, height: 11, background: 'var(--green)', borderRadius: 2 }} />
                  <span style={{ fontFamily: 'var(--mono)', fontSize: 9.5, color: 'var(--ink-soft)' }}>{b.raw != null ? b.raw.toFixed(2) : 'n/a'}</span>
                </div>
              </div>
            </div>
          ))}
          <div style={{ display: 'grid', gridTemplateColumns: '168px 1fr', gap: 10, marginTop: 8 }}>
            <span />
            <div style={{ position: 'relative', height: 16, borderTop: '1px solid var(--line)' }}>
              {ticks.map((t) => (
                <span key={t} style={{ position: 'absolute', left: `${(t / xMax) * 100}%`, fontFamily: 'var(--mono)', fontSize: 9, color: 'var(--ink-faint)', transform: 'translateX(-50%)', marginTop: 2 }}>{t}</span>
              ))}
            </div>
          </div>
          <p style={{ fontSize: 11.5, color: 'var(--ink-faint)', marginTop: 16, lineHeight: 1.5 }}>
            Absolute Vina binding score (kcal/mol) per target. The ML score is a target-agnostic activity prior, so it is identical across every target.
          </p>
        </div>

        <div>
          <h3 style={{ fontSize: 15, marginBottom: 10 }}>ADMET Safety Profile</h3>
          {admet ? <RadarChart axes={radarAxes} /> : <p style={{ fontSize: 13, color: 'var(--ink-faint)' }}>No ADMET record for this drug.</p>}
        </div>
      </div>
    </section>
  )
}
