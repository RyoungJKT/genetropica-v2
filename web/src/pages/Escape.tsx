import { useState } from 'react'
import { useEscape } from '../data/api'
import { useRegister, say } from '../state/register'
import { ChartTooltip } from '../components/ChartTooltip'
import { useInView } from '../lib/anim'
import type { EscapeDrug } from '../data/types'

const CLS_COLOR: Record<string, string> = { conserved: '#1F5740', intermediate: '#A8742C', variable: '#A8492C' }
const cap = (s: string) => s.replace(/_/g, ' ')
const title = (s: string) => { const t = cap(s); return t.charAt(0).toUpperCase() + t.slice(1) }
const tier = (d: number) => (d >= 73 ? '#1F5740' : d >= 66 ? '#A8742C' : '#A8492C')

type Tip = { x: number; y: number; node: React.ReactNode } | null

function Leaderboard({ drugs, sel, onSel }: { drugs: EscapeDrug[]; sel: string; onSel: (n: string) => void }) {
  const [ref, inView] = useInView<HTMLDivElement>()
  const [showAll, setShowAll] = useState(false)
  const [tip, setTip] = useState<Tip>(null)
  const max = drugs[0]?.durability ?? 100
  const shown = showAll ? drugs : drugs.slice(0, 18)
  return (
    <div ref={ref}>
      {shown.map((d, i) => {
        const active = d.name === sel
        return (
          <div
            key={d.name}
            onClick={() => onSel(d.name)}
            onMouseMove={(e) => setTip({ x: e.clientX, y: e.clientY, node: (
              <>
                <div style={{ fontWeight: 600, textTransform: 'capitalize' }}>{cap(d.name)}</div>
                <div style={{ opacity: 0.85 }}>{d.durability}% durable · mean grade {d.meanGrade}/9</div>
                <div style={{ opacity: 0.85 }}>{d.conserved} conserved · {d.variable} variable of {d.nContacts} contacts</div>
                {d.vina != null && <div style={{ opacity: 0.85 }}>Vina {d.vina} kcal/mol</div>}
              </>
            ) })}
            onMouseLeave={() => setTip(null)}
            style={{ display: 'grid', gridTemplateColumns: '150px 1fr 96px', gap: 12, alignItems: 'center', padding: '5px 8px', borderRadius: 8, cursor: 'pointer', background: active ? 'var(--paper-2)' : 'transparent', border: `1px solid ${active ? 'var(--line)' : 'transparent'}` }}
          >
            <span style={{ fontSize: 13, color: active ? 'var(--ink)' : 'var(--ink-soft)', textTransform: 'capitalize', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontWeight: active ? 600 : 400 }}>{cap(d.name)}</span>
            <div style={{ background: 'var(--paper-3)', borderRadius: 5, height: 14, overflow: 'hidden' }}>
              <div className="bar" style={{ width: inView ? `${(d.durability / max) * 100}%` : '0%', height: '100%', background: tier(d.durability), borderRadius: 5, transitionDelay: `${Math.min(i * 16, 420)}ms` }} />
            </div>
            <span style={{ fontFamily: 'var(--mono)', fontSize: 12, color: 'var(--ink-soft)' }}>{d.durability}% durable</span>
          </div>
        )
      })}
      {drugs.length > 18 && (
        <button onClick={() => setShowAll((v) => !v)} style={{ marginTop: 10, fontFamily: 'var(--mono)', fontSize: 10.5, letterSpacing: '.06em', textTransform: 'uppercase', color: 'var(--green)', background: 'none', border: 'none', cursor: 'pointer', padding: '4px 0' }}>
          {showAll ? 'Show top 18' : `Show all ${drugs.length} candidates`}
        </button>
      )}
      {tip && <ChartTooltip x={tip.x} y={tip.y}>{tip.node}</ChartTooltip>}
    </div>
  )
}

function GripDetail({ d }: { d: EscapeDrug }) {
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
        <span style={{ fontFamily: 'var(--serif)', fontSize: 30, color: tier(d.durability) }}>{d.durability}%<span style={{ fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--ink-faint)', marginLeft: 6 }}>durable</span></span>
      </div>
      <p style={{ fontSize: 12.5, color: 'var(--ink-faint)', margin: '2px 0 16px' }}>
        mean conservation grade {d.meanGrade}/9 across {d.nContacts} contacted residues{d.vina != null ? ` · Vina ${d.vina} kcal/mol` : ''}{d.keyContacts > 0 ? ` · ${d.keyContacts} catalytic` : ''}
      </p>

      <div style={{ display: 'flex', gap: 7, alignItems: 'flex-end', flexWrap: 'wrap', minHeight: 104 }} key={d.name}>
        {d.contacts.map((c, i) => (
          <div key={c.num} style={{ textAlign: 'center' }}
            onMouseMove={(e) => setTip({ x: e.clientX, y: e.clientY, node: (
              <>
                <div style={{ fontWeight: 600 }}>{c.res} {c.num}{c.key ? ' · catalytic' : ''}</div>
                <div style={{ opacity: 0.85 }}>conservation grade {c.grade}/9 · {c.cls}</div>
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
        {chip(d.conserved, 'conserved', CLS_COLOR.conserved)}
        {chip(d.intermediate, 'intermediate', CLS_COLOR.intermediate)}
        {chip(d.variable, 'variable', CLS_COLOR.variable)}
      </div>
      <p style={{ fontSize: 12, color: 'var(--ink-faint)', lineHeight: 1.55, marginTop: 14 }}>
        Taller, greener bars are residues the virus is least able to mutate without a fitness cost, so contacts there raise the barrier to resistance. Shorter, clay bars are variable positions the virus can change to escape.
      </p>
      {tip && <ChartTooltip x={tip.x} y={tip.y}>{tip.node}</ChartTooltip>}
    </div>
  )
}

export default function Escape() {
  const e = useEscape()
  const { reg } = useRegister()
  const [selName, setSelName] = useState<string | null>(null)
  const data = e.data
  const drugs = data?.drugs ?? []
  const sel = drugs.find((d) => d.name === selName) ?? drugs[0]

  return (
    <div className="wrap" style={{ padding: '56px 0' }}>
      <div className="eyebrow">Tool 09</div>
      <h1 style={{ fontSize: 'clamp(34px,5vw,60px)', fontWeight: 380, marginTop: 12 }}>Evolutionary Escape &amp; Durability</h1>
      <p style={{ color: 'var(--ink-soft)', maxWidth: 760, lineHeight: 1.65, margin: '14px 0 0' }}>
        {say(reg,
          'Which of these drugs would dengue find hardest to dodge by mutating? A drug that latches onto parts of the protein the virus cannot change without harming itself is durable; one that grips changeable parts is easy to escape. Each candidate is scored by how conserved the residues it touches are.',
          'A per-drug resistance-barrier estimate for DENV NS5: the mean ConSurf conservation grade (1 variable, 9 conserved) of the residues each docked pose contacts. Highly conserved contact sets imply a higher barrier to escape mutation; variable contact sets imply low-cost viral escape.')}
      </p>

      {!data && <p className="mono" style={{ marginTop: 20 }}>Loading escape analysis...</p>}

      {data && sel && (
        <>
          <div className="rstats" style={{ display: 'grid', gridTemplateColumns: 'repeat(3,minmax(0,1fr))', gap: 12, margin: '26px 0 4px', maxWidth: 720 }}>
            {[
              [`${data.bindingMean} vs ${data.nonbindingMean}`, 'binding-site vs rest conservation grade'],
              [`${drugs.length}`, 'drug-like NS5 candidates scored'],
              [title(drugs[0].name), `most durable · ${drugs[0].durability}%`],
            ].map(([v, l]) => (
              <div key={l} style={{ border: '1px solid var(--line)', borderRadius: 14, padding: '14px 16px', background: 'var(--paper)' }}>
                <div style={{ fontFamily: 'var(--serif)', fontSize: 26, fontWeight: 380, lineHeight: 1.05 }}>{v}</div>
                <div style={{ fontFamily: 'var(--mono)', fontSize: 10, letterSpacing: '.05em', textTransform: 'uppercase', color: 'var(--ink-faint)', marginTop: 8, lineHeight: 1.4 }}>{l}</div>
              </div>
            ))}
          </div>

          <div style={{ background: 'var(--paper-2)', border: '1px solid var(--line)', borderRadius: 12, padding: '15px 18px', margin: '18px 0 0', maxWidth: 820, fontSize: 13.5, color: 'var(--ink-soft)', lineHeight: 1.6 }}>
            A structure-and-conservation heuristic for dengue NS5, the one target with residue-level ConSurf data, not an experimental resistance assay. Binding-site residues are more conserved than the rest of the protein (grade {data.bindingMean} vs {data.nonbindingMean}); with few binding residues the gap is {data.mwSignificant ? 'significant' : <>not yet statistically significant (Mann-Whitney p = {data.mwP})</>}. Read it as a tie-breaker: among similarly-docked candidates, prefer the ones that grip conserved positions.
          </div>

          <div className="rstack" style={{ display: 'grid', gridTemplateColumns: 'minmax(0,1.05fr) minmax(0,1fr)', gap: 30, alignItems: 'start', marginTop: 30 }}>
            <div>
              <h3 style={{ fontSize: 22 }}>Durability leaderboard</h3>
              <p style={{ fontSize: 13.5, color: 'var(--ink-soft)', margin: '4px 0 14px', maxWidth: 560 }}>
                Every drug-like NS5 candidate, ranked by how conserved its contact residues are. Click one to see exactly where it grips.
              </p>
              <Leaderboard drugs={drugs} sel={sel.name} onSel={setSelName} />
            </div>
            <div>
              <h3 style={{ fontSize: 22, marginBottom: 14 }}>Where it grips NS5</h3>
              <GripDetail d={sel} />
            </div>
          </div>
        </>
      )}
    </div>
  )
}
