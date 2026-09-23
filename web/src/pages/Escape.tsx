import { useState } from 'react'
import { useEscape } from '../data/api'
import { ChartTooltip } from '../components/ChartTooltip'
import type { EscapeDrug } from '../data/types'
import { useT } from '../i18n'

const CLS_COLOR: Record<string, string> = { conserved: '#1F5740', intermediate: '#A8742C', variable: '#A8492C' }
const cap = (s: string) => s.replace(/_/g, ' ')

type Tip = { x: number; y: number; node: React.ReactNode } | null

/* Deliberately not a ranked list. Every candidate binds the same conserved pocket,
   so durability ties across the library and any ordering would be a tie-break
   dressed up as a finding. This is a selector: alphabetical, no bars, no winner. */
function CandidateList({ drugs, sel, onSel }: { drugs: EscapeDrug[]; sel: string; onSel: (n: string) => void }) {
  const { t } = useT()
  const [showAll, setShowAll] = useState(false)
  const [tip, setTip] = useState<Tip>(null)
  const sorted = [...drugs].sort((a, b) => a.name.localeCompare(b.name))
  const shown = showAll ? sorted : sorted.slice(0, 24)
  return (
    <div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(150px,1fr))', gap: 6 }}>
        {shown.map((d) => {
          const active = d.name === sel
          return (
            <button
              key={d.name}
              onClick={() => onSel(d.name)}
              onMouseMove={(e) => setTip({ x: e.clientX, y: e.clientY, node: (
                <>
                  <div style={{ fontWeight: 600, textTransform: 'capitalize' }}>{cap(d.name)}</div>
                  <div style={{ opacity: 0.85 }}>{d.nContacts} {t('contacted residues')} · {t('mean grade')} {d.meanGrade}/9</div>
                  <div style={{ opacity: 0.85 }}>{d.conserved} {t('conserved')} · {d.variable} {t('variable')}</div>
                  {d.vina != null && <div style={{ opacity: 0.85 }}>Vina {d.vina} kcal/mol</div>}
                </>
              ) })}
              onMouseLeave={() => setTip(null)}
              style={{
                textAlign: 'left', fontSize: 13, padding: '6px 10px', borderRadius: 8, cursor: 'pointer',
                textTransform: 'capitalize', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                background: active ? 'var(--paper-2)' : 'transparent',
                border: `1px solid ${active ? 'var(--line)' : 'transparent'}`,
                color: active ? 'var(--ink)' : 'var(--ink-soft)', fontWeight: active ? 600 : 400,
                fontFamily: 'inherit',
              }}
            >{cap(d.name)}</button>
          )
        })}
      </div>
      {sorted.length > 24 && (
        <button onClick={() => setShowAll((v) => !v)} style={{ marginTop: 10, fontFamily: 'var(--mono)', fontSize: 10.5, letterSpacing: '.06em', textTransform: 'uppercase', color: 'var(--green)', background: 'none', border: 'none', cursor: 'pointer', padding: '4px 0' }}>
          {showAll ? t('Show fewer') : `${t('Show all')} ${sorted.length} ${t('candidates')}`}
        </button>
      )}
      {tip && <ChartTooltip x={tip.x} y={tip.y}>{tip.node}</ChartTooltip>}
    </div>
  )
}

function GripDetail({ d }: { d: EscapeDrug }) {
  const { t } = useT()
  const [tip, setTip] = useState<Tip>(null)
  const chip = (n: number, label: string, color: string) => (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--ink-soft)' }}>
      <i style={{ width: 9, height: 9, borderRadius: '50%', background: color, display: 'inline-block' }} />{n} {label}
    </span>
  )
  return (
    <div style={{ border: '1px solid var(--line)', borderRadius: 16, background: 'var(--paper)', padding: 20 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: 12, flexWrap: 'wrap' }}>
        <h3 style={{ fontSize: 21, textTransform: 'capitalize' }}>{cap(d.name)}</h3>
        {/* the measured quantity, not a score: a rescaled version of this was the old durability rank */}
        <span style={{ fontFamily: 'var(--serif)', fontSize: 30, color: CLS_COLOR[d.meanGrade >= 7 ? 'conserved' : d.meanGrade <= 3 ? 'variable' : 'intermediate'] }}>
          {d.meanGrade}<span style={{ fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--ink-faint)', marginLeft: 6 }}>/9 {t('mean grade')}</span>
        </span>
      </div>
      <p style={{ fontSize: 12.5, color: 'var(--ink-faint)', margin: '2px 0 16px' }}>
        {t('across')} {d.nContacts} {t('contacted residues')}{d.vina != null ? ` · Vina ${d.vina} kcal/mol` : ''}{d.keyContacts > 0 ? ` · ${d.keyContacts} ${t('catalytic')}` : ''}
      </p>

      <div style={{ display: 'flex', gap: 7, alignItems: 'flex-end', flexWrap: 'wrap', minHeight: 104 }} key={d.name}>
        {d.contacts.map((c, i) => (
          <div key={c.num} style={{ textAlign: 'center' }}
            onMouseMove={(e) => setTip({ x: e.clientX, y: e.clientY, node: (
              <>
                <div style={{ fontWeight: 600 }}>{c.res} {c.num}{c.key ? ` · ${t('catalytic')}` : ''}</div>
                <div style={{ opacity: 0.85 }}>{t('conservation grade')} {c.grade}/9 · {t(c.cls)}</div>
              </>
            ) })}
            onMouseLeave={() => setTip(null)}>
            <div style={{ height: 16, fontSize: 10, color: 'var(--ink-faint)' }}>{c.key ? '▲' : ''}</div>
            <div className="grip-cell" style={{ width: 28, height: 24 + c.grade * 8, background: CLS_COLOR[c.cls], borderRadius: 4, animationDelay: `${i * 45}ms` }} />
            <div style={{ fontFamily: 'var(--mono)', fontSize: 9, color: 'var(--ink-faint)', marginTop: 5 }}>{c.num}</div>
          </div>
        ))}
      </div>

      <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', marginTop: 16, paddingTop: 14, borderTop: '1px solid var(--line)' }}>
        {chip(d.conserved, t('conserved'), CLS_COLOR.conserved)}
        {chip(d.intermediate, t('intermediate'), CLS_COLOR.intermediate)}
        {chip(d.variable, t('variable'), CLS_COLOR.variable)}
      </div>
      <p style={{ fontSize: 12, color: 'var(--ink-faint)', lineHeight: 1.55, marginTop: 14 }}>
        {t('Taller, greener bars are residues the virus is least able to mutate without a fitness cost, so contacts there raise the barrier to resistance. Shorter, clay bars are variable positions the virus can change to escape.')}
      </p>
      {tip && <ChartTooltip x={tip.x} y={tip.y}>{tip.node}</ChartTooltip>}
    </div>
  )
}

export default function Escape() {
  const { t } = useT()
  const e = useEscape()
  const [selName, setSelName] = useState<string | null>(null)
  const data = e.data
  const drugs = data?.drugs ?? []
  const byName = [...drugs].sort((a, b) => a.name.localeCompare(b.name))
  const sel = drugs.find((d) => d.name === selName) ?? byName[0]
  const contacted = data?.contacted ?? []
  const nConserved = contacted.filter((c) => c.cls === 'conserved').length

  return (
    <div className="wrap" style={{ padding: '56px 0' }}>
      <div className="eyebrow">{t('Tool 06')}</div>
      <h1 style={{ fontSize: 'clamp(34px,5vw,60px)', fontWeight: 380, marginTop: 12 }}>{t('Where These Drugs Grip NS5')}</h1>
      <p style={{ color: 'var(--ink-soft)', maxWidth: 760, lineHeight: 1.65, margin: '14px 0 0' }}>
        {t('Every candidate here docks into the catalytic site of dengue NS5. That is the pocket the virus uses to copy its own genome, and the part it can least afford to change. This page shows which residues each drug touches and how conserved those positions are across dengue and related flaviviruses. It does not rank the drugs; the section below explains why.')}
      </p>

      {!data && <p className="mono" style={{ marginTop: 20 }}>{t('Loading escape analysis...')}</p>}

      {data && sel && (
        <>
          <div className="rstats" style={{ display: 'grid', gridTemplateColumns: 'repeat(3,minmax(0,1fr))', gap: 12, margin: '26px 0 4px', maxWidth: 720 }}>
            {[
              [`${data.bindingMean} vs ${data.nonbindingMean}`, t('binding-site vs rest conservation grade')],
              [`${drugs.length}`, t('drug-like NS5 candidates mapped')],
              [`${nConserved} ${t('of')} ${contacted.length}`, t('contacted residues the virus cannot easily change')],
            ].map(([v, l]) => (
              <div key={l} style={{ border: '1px solid var(--line)', borderRadius: 14, padding: '14px 16px', background: 'var(--paper)' }}>
                <div style={{ fontFamily: 'var(--serif)', fontSize: 26, fontWeight: 380, lineHeight: 1.05 }}>{v}</div>
                <div style={{ fontFamily: 'var(--mono)', fontSize: 10, letterSpacing: '.05em', textTransform: 'uppercase', color: 'var(--ink-faint)', marginTop: 8, lineHeight: 1.4 }}>{l}</div>
              </div>
            ))}
          </div>

          <div style={{ background: 'var(--paper-2)', border: '1px solid var(--line)', borderRadius: 12, padding: '15px 18px', margin: '18px 0 0', maxWidth: 820, fontSize: 13.5, color: 'var(--ink-soft)', lineHeight: 1.6 }}>
            {t('A structure-and-conservation map for dengue NS5, the one target with residue-level ConSurf data, not an experimental resistance assay. Binding-site residues are more conserved than the rest of the protein')} ({t('grade')} {data.bindingMean} vs {data.nonbindingMean}); {t('with few binding residues the gap is')} {data.mwSignificant ? t('significant') : <>{t('not yet statistically significant')} (Mann-Whitney p = {data.mwP})</>}. {t('Poses come from the catalytic site; an earlier version of this page used poses from a search box that never contained it. The structure is a DENV-3 polymerase and its residue numbers are mapped onto the DENV-2 conservation frame by sequence alignment.')}
          </div>

          <div className="rstack" style={{ display: 'grid', gridTemplateColumns: 'minmax(0,1.05fr) minmax(0,1fr)', gap: 30, alignItems: 'start', marginTop: 30 }}>
            <div>
              <h3 style={{ fontSize: 22 }}>{t('Candidates')}</h3>
              <p style={{ fontSize: 13.5, color: 'var(--ink-soft)', margin: '4px 0 14px', maxWidth: 560 }}>
                {t('Every drug-like NS5 candidate, listed alphabetically. Pick one to see exactly where it grips.')}
              </p>
              <CandidateList drugs={drugs} sel={sel.name} onSel={setSelName} />
            </div>
            <div>
              <h3 style={{ fontSize: 22, marginBottom: 14 }}>{t('Where it grips NS5')}</h3>
              <GripDetail d={sel} />
            </div>
          </div>

          <section style={{ marginTop: 44, borderTop: '1px solid var(--line)', paddingTop: 26 }}>
            <h3 style={{ fontSize: 22, fontWeight: 400 }}>{t('Why there is no ranking')}</h3>
            <p style={{ color: 'var(--ink-soft)', maxWidth: 780, lineHeight: 1.65, margin: '12px 0 0', fontSize: 14.5 }}>
              {t('An earlier version of this page ranked candidates by a durability score and named a winner. That ranking came from poses docked into a box whose centre sat 30 Å from the catalytic motif, so it described a region that is not the drug target.')}
            </p>
            <p style={{ color: 'var(--ink-soft)', maxWidth: 780, lineHeight: 1.65, margin: '12px 0 0', fontSize: 14.5 }}>
              {t('Re-docking at the correct site fixed the poses but removed the ranking. Because every candidate now binds the same highly conserved pocket, their scores bunch together: the median gap between neighbouring candidates is zero, and dropping any single contact moves a candidate further than the gap separating it from the next. An ordering built on that would be a tie-break presented as a finding.')}
            </p>
            <p style={{ color: 'var(--ink-soft)', maxWidth: 780, lineHeight: 1.65, margin: '12px 0 0', fontSize: 14.5 }}>
              {t('The wider spread the old leaderboard showed was an artefact of the error, not a signal. What survives the correction is the map above: where each candidate binds, and how conserved that pocket is. The retrospective benchmark on the Validation page is the companion result. At this site the docking scores did not separate known inhibitors from decoys.')}
            </p>
          </section>
        </>
      )}
    </div>
  )
}
