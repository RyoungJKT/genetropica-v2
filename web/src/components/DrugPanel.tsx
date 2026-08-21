import { useRef, useEffect, useState } from 'react'
import type { Drug, Field, AdmetRow, LitRef } from '../data/types'
import { RadarChart } from './RadarChart'
import { ChartTooltip } from './ChartTooltip'
import { useInView } from '../lib/anim'
import { useT } from '../i18n'

function Meta({ k, v }: { k: string; v: string }) {
  return (
    <div>
      <div style={{ fontFamily: 'var(--mono)', fontSize: 10, letterSpacing: '.08em', textTransform: 'uppercase', color: 'var(--ink-faint)' }}>{k}</div>
      <div style={{ fontSize: 15, color: 'var(--ink)', marginTop: 3, overflowWrap: 'anywhere' }}>{v}</div>
    </div>
  )
}

/** Inline per-drug detail: metadata, cross-target binding bars (Vina + the constant ML prior), ADMET radar. */
export function DrugPanel({ drug, field, admet, order, tName, literature = [] }: { drug: Drug; field: Field; admet?: AdmetRow; order: string[]; tName: (id: string) => string; literature?: LitRef[] }) {
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

  const radarAxes = admet
    ? [
        { label: t('Lipinski Compliance'), value: admet.lipinski },
        { label: t('Oral Bioavailability'), value: admet.bioavail },
        { label: t('Overall Safety'), value: admet.pass },
        { label: t('hERG Safety'), value: 1 - admet.herg },
        { label: t('Hepato Safety'), value: 1 - admet.hepatotox },
      ]
    : []

  const byTarget: Record<string, LitRef[]> = {}
  for (const r of literature) (byTarget[r.target] ??= []).push(r)
  const tierColor = (t: string) => (['direct_target', 'mechanistic', 'same_pathogen_phenotypic'].includes(t) ? 'var(--green)' : t === 'weak_keyword' ? 'var(--ink-faint)' : 'var(--gold)')
  const verdictColor = (v?: string) => (v === 'supports' ? 'var(--green)' : v === 'related' ? 'var(--gold)' : v === 'adverse' ? 'var(--clay)' : 'var(--ink-faint)')

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

      <div ref={chartsRef} className="rstack" style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1.15fr) minmax(0, 1fr)', gap: 32, alignItems: 'start' }}>
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
              onMouseMove={(e) => setTip({ x: e.clientX, y: e.clientY, title: b.name, value: `Vina ${b.raw != null ? b.raw.toFixed(2) : 'n/a'} kcal/mol  •  ML ${ml.toFixed(2)}` })}
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
            {t('Absolute Vina binding score (kcal/mol) per target. The ML score is a target-agnostic activity prior, so it is identical across every target.')}
          </p>
        </div>

        <div>
          <h3 style={{ fontSize: 15, marginBottom: 10 }}>{t('ADMET Safety Profile')}</h3>
          {admet ? <RadarChart axes={radarAxes} /> : <p style={{ fontSize: 13, color: 'var(--ink-faint)' }}>{t('No ADMET record for this drug.')}</p>}
        </div>
      </div>

      {Object.keys(byTarget).length > 0 ? (
        <div style={{ marginTop: 32 }}>
          <h3 style={{ fontSize: 15, marginBottom: 4 }}>{t('Literature evidence')}</h3>
          <p style={{ fontSize: 11.5, color: 'var(--ink-faint)', margin: '0 0 12px', maxWidth: 720, lineHeight: 1.5 }}>
            {t('PubMed references linking this drug to each target (keyword-mined, then language-model reviewed where an "AI" verdict is shown). Evidence is a hint, not proof of activity.')}
          </p>
          {Object.entries(byTarget).map(([tid, refs]) => (
            <div key={tid} style={{ marginBottom: 14 }}>
              <div style={{ fontFamily: 'var(--mono)', fontSize: 10, letterSpacing: '.06em', textTransform: 'uppercase', color: 'var(--clay)', marginBottom: 6 }}>{tName(tid)} · {refs.length} {refs.length === 1 ? t('ref') : t('refs')}</div>
              {refs.map((r) => (
                <div key={r.pmid} style={{ display: 'grid', gridTemplateColumns: '1fr auto', gap: 12, padding: '7px 0', borderBottom: '1px solid var(--line)', alignItems: 'start' }}>
                  <div>
                    <a href={`https://pubmed.ncbi.nlm.nih.gov/${r.pmid}/`} target="_blank" rel="noopener" style={{ fontSize: 13, color: 'var(--ink)', lineHeight: 1.4 }}>{r.title}</a>
                    {r.llm_verdict ? (
                      <div style={{ fontSize: 11, color: 'var(--ink-faint)', marginTop: 2, lineHeight: 1.45 }}>PMID {r.pmid} · <span style={{ color: verdictColor(r.llm_verdict), fontWeight: 600 }}>{t('AI:')} {r.llm_verdict}</span>{r.llm_rel ? ` · ${r.llm_rel}` : ''}{r.llm_note ? <span style={{ color: 'var(--ink-soft)' }}> — {r.llm_note}</span> : null}</div>
                    ) : (
                      <div style={{ fontSize: 11, color: 'var(--ink-faint)', marginTop: 2 }}>PMID {r.pmid} · {r.rel} · <span style={{ color: tierColor(r.tier) }}>{r.tier.replace(/_/g, ' ')}</span></div>
                    )}
                  </div>
                  <span style={{ fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--ink-soft)', whiteSpace: 'nowrap' }}>{r.llm_conf != null ? r.llm_conf.toFixed(2) : r.conf != null ? r.conf.toFixed(2) : ''}</span>
                </div>
              ))}
            </div>
          ))}
        </div>
      ) : (
        <p style={{ marginTop: 28, fontSize: 13, color: 'var(--ink-faint)' }}>{t('No literature references found for this drug.')}</p>
      )}
      {tip && (
        <ChartTooltip x={tip.x} y={tip.y}>
          <div style={{ fontWeight: 600 }}>{tip.title}</div>
          <div style={{ opacity: 0.85 }}>{tip.value}</div>
        </ChartTooltip>
      )}
    </section>
  )
}
