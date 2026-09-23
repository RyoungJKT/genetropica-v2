import { useRef, useEffect, useState } from 'react'
import type { Drug, Field, DengueRef } from '../data/types'
import { useDengueLit } from '../data/api'
import { ChartTooltip } from './ChartTooltip'
import { useInView } from '../lib/anim'
import { useT } from '../i18n'
import { Ns5DockingNote } from './Ns5DockingNote'

function Meta({ k, v }: { k: string; v: string }) {
  return (
    <div>
      <div style={{ fontFamily: 'var(--mono)', fontSize: 10, letterSpacing: '.08em', textTransform: 'uppercase', color: 'var(--ink-faint)' }}>{k}</div>
      <div style={{ fontSize: 15, color: 'var(--ink)', marginTop: 3, overflowWrap: 'anywhere' }}>{v}</div>
    </div>
  )
}

const FINDING_COLOR: Record<DengueRef['finding'], string> = {
  'inhibits': 'var(--green)', 'no benefit': 'var(--clay)', 'mixed': 'var(--gold)', 'mechanism': 'var(--ink-soft)',
}

/** Published dengue work on this drug: real PubMed records, each labelled with what it found. */
function DengueEvidence({ drug }: { drug: string }) {
  const { t } = useT()
  const lit = useDengueLit()
  if (!lit.data) return null
  const refs = lit.data.drugs[drug] ?? []
  const tag = (label: string, color: string, solid = false) => (
    <span style={{ fontFamily: 'var(--mono)', fontSize: 9.5, letterSpacing: '.06em', textTransform: 'uppercase', padding: '2px 7px', borderRadius: 100, whiteSpace: 'nowrap', color: solid ? 'var(--paper)' : color, background: solid ? color : 'transparent', border: `1px solid ${color}` }}>{label}</span>
  )
  return (
    <div style={{ marginTop: 32 }}>
      <h3 style={{ fontSize: 15, marginBottom: 4 }}>{t('Published dengue research')}</h3>
      <p style={{ fontSize: 11.5, color: 'var(--ink-faint)', margin: '0 0 12px', maxWidth: 720, lineHeight: 1.5 }}>
        {t('Papers naming this drug and dengue in the title, each read and labelled by what it found. A paper here is not a recommendation: several of these drugs failed in patients. Summarised from abstracts only.')}
      </p>
      {refs.length === 0 ? (
        <p style={{ fontSize: 13, color: 'var(--ink-faint)' }}>{t('No published test of this drug against dengue was found.')}</p>
      ) : refs.map((r) => (
        <div key={r.pmid} style={{ padding: '9px 0', borderBottom: '1px solid var(--line)' }}>
          <div style={{ display: 'flex', gap: 6, alignItems: 'center', flexWrap: 'wrap', marginBottom: 4 }}>
            {tag(t(r.kind), 'var(--ink-faint)')}
            {tag(t(r.finding), FINDING_COLOR[r.finding], true)}
            <span style={{ fontFamily: 'var(--mono)', fontSize: 10.5, color: 'var(--ink-faint)' }}>{r.journal} · {r.year}</span>
          </div>
          <a href={`https://pubmed.ncbi.nlm.nih.gov/${r.pmid}/`} target="_blank" rel="noopener" style={{ fontSize: 13, color: 'var(--ink)', lineHeight: 1.4 }}>{r.title}</a>
          <div style={{ fontSize: 12, color: 'var(--ink-soft)', marginTop: 3, lineHeight: 1.5 }}>{t(r.note)}</div>
        </div>
      ))}
    </div>
  )
}

/** Inline per-drug detail: metadata, cross-target binding bars (Vina + the constant ML prior), dengue papers. */
export function DrugPanel({ drug, field, order, tName, ns5NoteShown = false }: { drug: Drug; field: Field; order: string[]; tName: (id: string) => string; ns5NoteShown?: boolean }) {
  const { t } = useT()
  const ref = useRef<HTMLDivElement>(null)
  const firstRender = useRef(true)
  useEffect(() => {
    // Don't yank the page down on the initial default selection; only scroll on later picks.
    if (firstRender.current) {
      firstRender.current = false
      return
    }
    ref.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  }, [drug.name])

  const [tip, setTip] = useState<{ x: number; y: number; title: string; value: string } | null>(null)
  const [chartsRef, inView] = useInView<HTMLDivElement>()
  const bars = order.map((tid) => {
    const p = (field[tid] ?? []).find((x) => x.name === drug.name)
    return { tid, name: tName(tid), vina: p ? Math.abs(p.vina) : 0, raw: p ? p.vina : null }
  })
  const ml = drug.ml ?? 0
  const xMax = Math.max(10, ...bars.map((b) => b.vina), ml)
  const ticks = [0, 2, 4, 6, 8, 10].filter((t) => t <= xMax)

  return (
    <section ref={ref} style={{ marginTop: 36, scrollMarginTop: 80 }}>
      <h2 style={{ fontSize: 32, textTransform: 'capitalize', fontWeight: 380 }}>{drug.name.replace(/_/g, ' ')}</h2>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: 18, marginTop: 16 }}>
        <Meta k={t('DrugBank ID')} v={drug.drugbank_id ?? t('None')} />
        <Meta k={t('Indication')} v={drug.indication ?? '-'} />
        <Meta k={t('Molecular Weight')} v={`${Math.round(drug.molecular_weight)} Da`} />
        <Meta k="LogP" v={drug.logp != null ? drug.logp.toFixed(2) : '-'} />
      </div>
      {drug.smiles && (
        <div style={{ marginTop: 16 }}>
          <div style={{ fontFamily: 'var(--mono)', fontSize: 10, letterSpacing: '.08em', textTransform: 'uppercase', color: 'var(--ink-faint)', marginBottom: 4 }}>SMILES</div>
          <div style={{ fontFamily: 'var(--mono)', fontSize: 12.5, color: 'var(--ink)', background: 'var(--paper-2)', border: '1px solid var(--line)', borderRadius: 10, padding: '10px 12px', overflowX: 'auto', whiteSpace: 'nowrap' }}>{drug.smiles}</div>
        </div>
      )}

      <hr style={{ border: 0, borderTop: '1px solid var(--line)', margin: '28px 0' }} />

      <div ref={chartsRef} style={{ maxWidth: 760 }}>
        <div>
          <h3 style={{ fontSize: 15, marginBottom: 4 }}>{t('Binding Scores Across Targets')}</h3>
          <div style={{ display: 'flex', gap: 16, margin: '6px 0 14px', fontSize: 11, fontFamily: 'var(--mono)', color: 'var(--ink-soft)' }}>
            <span><span style={{ display: 'inline-block', width: 10, height: 10, background: 'var(--green)', borderRadius: 2, marginRight: 6, verticalAlign: 'middle' }} />{t('Vina |score|')}</span>
            <span><span style={{ display: 'inline-block', width: 10, height: 10, background: 'var(--gold)', borderRadius: 2, marginRight: 6, verticalAlign: 'middle' }} />{t('ML |score|')}</span>
          </div>
          {bars.map((b, i) => (
            <div
              key={b.tid}
              style={{ display: 'grid', gridTemplateColumns: '168px 1fr', gap: 10, alignItems: 'center', margin: '9px 0', cursor: 'pointer' }}
              onMouseMove={(e) => setTip({ x: e.clientX, y: e.clientY, title: b.name, value: `Vina ${b.raw != null ? b.raw.toFixed(2) : t('n/a')} kcal/mol  •  ML ${ml.toFixed(2)}` })}
              onMouseLeave={() => setTip(null)}
            >
              <span style={{ fontSize: 11.5, color: 'var(--ink-soft)', textAlign: 'right', lineHeight: 1.2 }}>{b.name}</span>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, height: 9 }}>
                  <div className="bar" style={{ width: inView ? `${(ml / xMax) * 100}%` : '0%', height: 7, background: 'var(--gold)', borderRadius: 2, minWidth: inView && ml > 0 ? 2 : 0, transitionDelay: `${i * 40}ms` }} />
                  <span style={{ fontFamily: 'var(--mono)', fontSize: 9.5, color: 'var(--ink-faint)' }}>{ml.toFixed(2)}</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, height: 13, marginTop: 2 }}>
                  <div className="bar" style={{ width: inView ? `${(b.vina / xMax) * 100}%` : '0%', height: 11, background: 'var(--green)', borderRadius: 2, transitionDelay: `${i * 40}ms` }} />
                  <span style={{ fontFamily: 'var(--mono)', fontSize: 9.5, color: 'var(--ink-soft)' }}>{b.raw != null ? b.raw.toFixed(2) : t('n/a')}</span>
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
            {t('Absolute Vina binding score (kcal/mol) per target. The ML score is a target-agnostic activity prior, so it is identical across every target.')}
          </p>
          {!ns5NoteShown && <Ns5DockingNote style={{ fontSize: 11.5, margin: '8px 0 0', padding: '7px 11px' }} />}
        </div>
      </div>

      <DengueEvidence drug={drug.name} />

      {tip && (
        <ChartTooltip x={tip.x} y={tip.y}>
          <div style={{ fontWeight: 600 }}>{tip.title}</div>
          <div style={{ opacity: 0.85 }}>{tip.value}</div>
        </ChartTooltip>
      )}
    </section>
  )
}
