import { useState, type ReactNode } from 'react'
import { useAdmet, useAdmetProfiles, useDrugs, useField } from '../data/api'
import { bucketOf } from '../lib/buckets'
import type { Drug, AdmetRow, AdmetProfile } from '../data/types'
import { ChartTooltip } from '../components/ChartTooltip'
import { useInView, useCountUp } from '../lib/anim'
import { useT } from '../i18n'

type Tip = { x: number; y: number; title: string; value: string }

function band(v: number) {
  if (v < 0.3) return { label: 'low', color: 'var(--green)' }
  if (v < 0.6) return { label: 'medium', color: 'var(--gold)' }
  return { label: 'high', color: 'var(--clay)' }
}

function H3({ children }: { children: ReactNode }) {
  return <h3 style={{ fontSize: 22, marginBottom: 4 }}>{children}</h3>
}
function Lede({ children }: { children: ReactNode }) {
  return <p style={{ fontSize: 13.5, color: 'var(--ink-soft)', margin: '4px 0 14px', maxWidth: 820, lineHeight: 1.6 }}>{children}</p>
}

// ── Section 1: drug-likeness filter summary ──────────────────────────────
function FilterSummary({ profiles }: { profiles: AdmetProfile[] }) {
  const { t } = useT()
  const [ref, inView] = useInView<HTMLDivElement>()
  const total = profiles.length || 1
  const filters: [string, (p: AdmetProfile) => boolean][] = [
    ['Lipinski', (p) => p.lipinski],
    ['Veber', (p) => p.veber],
    ['Ghose', (p) => p.ghose],
    ['Egan', (p) => p.egan],
    [t('PAINS clean'), (p) => p.pains.length === 0],
  ]
  const counts = filters.map(([, f]) => profiles.filter(f).length)
  return (
    <div ref={ref}>
      <div className="rstats" style={{ display: 'grid', gridTemplateColumns: 'repeat(5,1fr)', gap: 12 }}>
        {filters.map(([label], i) => (
          <FilterCard key={label} label={label} value={counts[i]} total={total} active={inView} />
        ))}
      </div>
      <div style={{ marginTop: 20, display: 'flex', flexDirection: 'column', gap: 9, maxWidth: 720 }}>
        {filters.map(([label], i) => {
          const pct = Math.round((counts[i] / total) * 100)
          return (
            <div key={label} style={{ display: 'grid', gridTemplateColumns: '92px 1fr 42px', gap: 10, alignItems: 'center' }}>
              <span style={{ fontSize: 12, color: 'var(--ink-soft)', textAlign: 'right' }}>{label}</span>
              <div style={{ height: 12, background: 'var(--paper-3)', borderRadius: 100, overflow: 'hidden' }}>
                <div className="bar" style={{ height: '100%', width: inView ? `${pct}%` : '0%', background: pct >= 50 ? 'var(--green)' : 'var(--clay)', borderRadius: 100, transitionDelay: `${i * 50}ms` }} />
              </div>
              <span style={{ fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--ink)' }}>{pct}%</span>
            </div>
          )
        })}
      </div>
      <p style={{ fontSize: 12, color: 'var(--ink-faint)', marginTop: 14, maxWidth: 760, lineHeight: 1.6 }}>
        {t('Lipinski (MW ≤500, LogP ≤5, HBD ≤5, HBA ≤10) and Veber (TPSA ≤140, rotatable bonds ≤10) gauge oral drug-likeness; Ghose bounds the property ranges; Egan flags passive gut absorption; PAINS clean means no pan-assay-interference substructures.')}
      </p>
    </div>
  )
}
function FilterCard({ label, value, total, active }: { label: string; value: number; total: number; active: boolean }) {
  const n = useCountUp(value, active)
  return (
    <div style={{ border: '1px solid var(--line)', borderRadius: 14, padding: '14px 16px', background: 'var(--paper)' }}>
      <div style={{ fontFamily: 'var(--mono)', fontSize: 10, letterSpacing: '.06em', textTransform: 'uppercase', color: 'var(--ink-faint)' }}>{label}</div>
      <div style={{ fontSize: 30, fontWeight: 380, marginTop: 6, lineHeight: 1 }}>{n}<span style={{ fontSize: 15, color: 'var(--ink-faint)' }}>/{total}</span></div>
    </div>
  )
}

// ── Section 2: physicochemical radar ─────────────────────────────────────
const RADAR_AXES: { label: string; key: keyof AdmetProfile['desc']; lim: number }[] = [
  { label: 'MW', key: 'mw', lim: 500 },
  { label: 'LogP', key: 'logp', lim: 5 },
  { label: 'TPSA', key: 'tpsa', lim: 140 },
  { label: 'HBD', key: 'hbd', lim: 5 },
  { label: 'HBA', key: 'hba', lim: 10 },
  { label: 'RotB', key: 'rot', lim: 10 },
]
function PhysChemRadar({ p }: { p: AdmetProfile }) {
  const { t } = useT()
  const [tip, setTip] = useState<Tip | null>(null)
  const [ref, inView] = useInView<SVGSVGElement>()
  const W = 440, H = 360, cx = W / 2, cy = H / 2, R = 120
  const n = RADAR_AXES.length
  const ratios = RADAR_AXES.map((a) => Math.max(0, p.desc[a.key]) / a.lim)
  const maxR = Math.max(1.25, ...ratios)
  const ang = (i: number) => (i / n) * Math.PI * 2 - Math.PI / 2
  const at = (i: number, r: number): [number, number] => [cx + (r / maxR) * R * Math.cos(ang(i)), cy + (r / maxR) * R * Math.sin(ang(i))]
  const poly = (r: (i: number) => number) => RADAR_AXES.map((_, i) => at(i, r(i)).join(',')).join(' ')
  const dataPts = RADAR_AXES.map((_, i) => at(i, ratios[i]).join(',')).join(' ')
  return (
    <>
      <svg ref={ref} viewBox={`0 0 ${W} ${H}`} width="100%" style={{ overflow: 'visible', display: 'block', maxWidth: 440 }} role="img" aria-label={t('Physicochemical radar')}>
        {[0.5, 1, maxR].map((f) => <polygon key={f} points={poly(() => f)} fill="none" stroke="var(--line)" strokeWidth={1} />)}
        {RADAR_AXES.map((_, i) => { const [x, y] = at(i, maxR); return <line key={i} x1={cx} y1={cy} x2={x} y2={y} stroke="var(--line)" strokeWidth={1} /> })}
        {/* limit ring (ratio 1.0) */}
        <polygon points={poly(() => 1)} fill="none" stroke="var(--green)" strokeWidth={1.5} strokeDasharray="4 3" />
        <g className="reveal-scale" style={{ transform: inView ? 'scale(1)' : 'scale(0.3)', opacity: inView ? 1 : 0 }}>
          <polygon points={dataPts} fill="var(--teal)" fillOpacity={0.2} stroke="var(--teal)" strokeWidth={2} strokeLinejoin="round" />
          {RADAR_AXES.map((a, i) => {
            const [x, y] = at(i, ratios[i])
            return (
              <g key={a.label} style={{ cursor: 'pointer' }}
                onMouseMove={(e) => setTip({ x: e.clientX, y: e.clientY, title: a.label, value: `${p.desc[a.key]} (${t('limit')} ${a.lim})` })}
                onMouseLeave={() => setTip(null)}>
                <circle cx={x} cy={y} r={11} fill="transparent" />
                <circle cx={x} cy={y} r={3.5} fill="var(--teal)" />
              </g>
            )
          })}
        </g>
        {RADAR_AXES.map((a, i) => {
          const [x, y] = at(i, maxR + 0.12 * maxR)
          const anchor = Math.abs(x - cx) < 6 ? 'middle' : x > cx ? 'start' : 'end'
          return <text key={a.label} x={x} y={y} fontSize={11} fill="var(--ink-soft)" textAnchor={anchor} dominantBaseline="middle">{a.label}</text>
        })}
      </svg>
      {tip && <ChartTooltip x={tip.x} y={tip.y}><div style={{ fontWeight: 600 }}>{tip.title}</div><div style={{ opacity: 0.85 }}>{tip.value}</div></ChartTooltip>}
    </>
  )
}

// ── Section 3: BOILED-Egg absorption ─────────────────────────────────────
function BoiledEgg({ profiles }: { profiles: AdmetProfile[] }) {
  const { t } = useT()
  const [tip, setTip] = useState<Tip | null>(null)
  const W = 760, H = 440, m = { l: 52, r: 16, t: 14, b: 44 }
  const iw = W - m.l - m.r, ih = H - m.t - m.b
  const xLo = -3, xHi = 8, yLo = 0, yHi = 180
  const X = (v: number) => m.l + ((Math.max(xLo, Math.min(xHi, v)) - xLo) / (xHi - xLo)) * iw
  const Y = (v: number) => m.t + (1 - (Math.max(yLo, Math.min(yHi, v)) - yLo) / (yHi - yLo)) * ih
  const cat = (p: AdmetProfile) => (p.bbb === 'Yes' ? 'bbb' : p.gi === 'High' ? 'gi' : 'low')
  const COL = { bbb: 'var(--gold)', gi: 'var(--teal)', low: 'var(--clay)' }
  return (
    <div style={{ border: '1px solid var(--line)', borderRadius: 14, background: 'var(--paper)', padding: '14px 16px 8px', maxWidth: 760 }}>
      <svg viewBox={`0 0 ${W} ${H}`} width="100%" style={{ display: 'block' }}>
        {/* egg white (GI absorption) */}
        <ellipse cx={X(2.6)} cy={Y(71)} rx={(X(6.5) - X(-1.3)) / 2} ry={(Y(0) - Y(142)) / 2} fill="rgba(44,110,107,.10)" stroke="var(--teal)" strokeWidth={1} strokeDasharray="3 3" />
        {/* yolk (BBB) */}
        <ellipse cx={X(2.8)} cy={Y(28)} rx={(X(5) - X(0.4)) / 2} ry={(Y(0) - Y(74)) / 2} fill="rgba(168,116,44,.16)" stroke="var(--gold)" strokeWidth={1} strokeDasharray="3 3" />
        {[0, 35, 70, 105, 140, 175].map((t) => (
          <g key={t}><line x1={m.l} y1={Y(t)} x2={W - m.r} y2={Y(t)} stroke="var(--line)" strokeWidth={0.5} opacity={0.6} /><text x={m.l - 7} y={Y(t)} textAnchor="end" dominantBaseline="middle" fontFamily="var(--mono)" fontSize={9} fill="var(--ink-faint)">{t}</text></g>
        ))}
        {[-2, 0, 2, 4, 6, 8].map((t) => <text key={t} x={X(t)} y={H - 26} textAnchor="middle" fontFamily="var(--mono)" fontSize={9} fill="var(--ink-faint)">{t}</text>)}
        {profiles.map((p) => {
          const c = cat(p)
          return (
            <circle key={p.name} cx={X(p.desc.logp)} cy={Y(p.desc.tpsa)} r={5} fill={COL[c]} fillOpacity={0.85} stroke="var(--paper)" strokeWidth={0.8} style={{ cursor: 'pointer' }}
              onMouseMove={(e) => setTip({ x: e.clientX, y: e.clientY, title: p.name.replace(/_/g, ' '), value: `LogP ${p.desc.logp} · TPSA ${p.desc.tpsa} · ${c === 'bbb' ? t('BBB permeant') : c === 'gi' ? t('High GI') : t('Low absorption')}` })}
              onMouseLeave={() => setTip(null)} />
          )
        })}
        <text x={m.l + iw / 2} y={H - 6} textAnchor="middle" fontFamily="var(--mono)" fontSize={10} fill="var(--ink-soft)">LogP</text>
        <text transform={`translate(13,${m.t + ih / 2}) rotate(-90)`} textAnchor="middle" fontFamily="var(--mono)" fontSize={10} fill="var(--ink-soft)">TPSA (Å²)</text>
      </svg>
      <div style={{ display: 'flex', gap: 18, flexWrap: 'wrap', fontSize: 12, color: 'var(--ink-soft)', paddingLeft: 40, marginTop: 2 }}>
        {([['gi', 'High GI absorption'], ['bbb', 'Blood-brain-barrier permeant'], ['low', 'Low absorption']] as const).map(([k, label]) => (
          <span key={k} style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}><span style={{ width: 10, height: 10, borderRadius: '50%', background: COL[k] }} />{t(label)}</span>
        ))}
      </div>
      {tip && <ChartTooltip x={tip.x} y={tip.y}><div style={{ fontWeight: 600, textTransform: 'capitalize' }}>{tip.title}</div><div style={{ opacity: 0.85 }}>{tip.value}</div></ChartTooltip>}
    </div>
  )
}

// ── Section 4: structural alerts ─────────────────────────────────────────
function AlertsTable({ profiles }: { profiles: AdmetProfile[] }) {
  const { t } = useT()
  const flagged = profiles.filter((p) => p.pains.length || p.brenk.length)
  const painsClean = profiles.filter((p) => p.pains.length === 0).length
  const brenkClean = profiles.filter((p) => p.brenk.length === 0).length
  const td = { padding: '8px 12px', fontSize: 13, borderBottom: '1px solid var(--line)', verticalAlign: 'top' as const }
  return (
    <div>
      <div style={{ display: 'flex', gap: 24, marginBottom: 12, fontFamily: 'var(--mono)', fontSize: 12, color: 'var(--ink-soft)' }}>
        <span>{t('PAINS clean:')} <b style={{ color: 'var(--ink)' }}>{painsClean}/{profiles.length}</b></span>
        <span>{t('Brenk clean:')} <b style={{ color: 'var(--ink)' }}>{brenkClean}/{profiles.length}</b></span>
      </div>
      {flagged.length ? (
        <div style={{ border: '1px solid var(--line)', borderRadius: 14, overflow: 'auto', maxHeight: 360, background: 'var(--paper)', maxWidth: 820 }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead><tr>{['Drug', 'PAINS alerts', 'Brenk alerts'].map((h) => <th key={h} style={{ position: 'sticky', top: 0, background: 'var(--paper-2)', textAlign: 'left', padding: '9px 12px', fontFamily: 'var(--mono)', fontSize: 10, letterSpacing: '.06em', textTransform: 'uppercase', color: 'var(--ink-faint)', borderBottom: '1px solid var(--line)' }}>{t(h)}</th>)}</tr></thead>
            <tbody>
              {flagged.map((p) => (
                <tr key={p.name}>
                  <td style={{ ...td, textTransform: 'capitalize', whiteSpace: 'nowrap' }}>{p.name.replace(/_/g, ' ')}</td>
                  <td style={{ ...td, color: p.pains.length ? 'var(--clay)' : 'var(--ink-faint)' }}>{p.pains.length ? p.pains.join(', ') : t('none')}</td>
                  <td style={{ ...td, color: p.brenk.length ? 'var(--gold)' : 'var(--ink-faint)' }}>{p.brenk.length ? p.brenk.join(', ') : t('none')}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : <p style={{ fontSize: 14, color: 'var(--green)' }}>{t('All drugs are free of PAINS and Brenk structural alerts.')}</p>}
    </div>
  )
}

// ── Section 5: property heatmap ──────────────────────────────────────────
const HM_COLS: { label: string; ok: (p: AdmetProfile) => boolean }[] = [
  { label: 'Lipinski', ok: (p) => p.lipinski },
  { label: 'Veber', ok: (p) => p.veber },
  { label: 'Ghose', ok: (p) => p.ghose },
  { label: 'Egan', ok: (p) => p.egan },
  { label: 'PAINS', ok: (p) => p.pains.length === 0 },
  { label: 'Brenk', ok: (p) => p.brenk.length === 0 },
  { label: 'GI abs.', ok: (p) => p.gi === 'High' },
  { label: 'BBB', ok: (p) => p.bbb === 'Yes' },
]
function PropertyHeatmap({ profiles }: { profiles: AdmetProfile[] }) {
  const { t } = useT()
  const [ref, inView] = useInView<HTMLDivElement>()
  const [tip, setTip] = useState<Tip | null>(null)
  const cols = `150px repeat(${HM_COLS.length}, 1fr)`
  return (
    <div ref={ref}>
      <div style={{ border: '1px solid var(--line)', borderRadius: 14, overflow: 'auto', maxHeight: 540, background: 'var(--paper)' }}>
        <div style={{ display: 'grid', gridTemplateColumns: cols, position: 'sticky', top: 0, background: 'var(--paper-2)', zIndex: 1, borderBottom: '1px solid var(--line)' }}>
          <div style={{ padding: '8px 12px', fontFamily: 'var(--mono)', fontSize: 10, letterSpacing: '.05em', textTransform: 'uppercase', color: 'var(--ink-faint)' }}>{t('Drug')}</div>
          {HM_COLS.map((c) => <div key={c.label} style={{ padding: '8px 4px', fontFamily: 'var(--mono)', fontSize: 9.5, letterSpacing: '.04em', textTransform: 'uppercase', color: 'var(--ink-faint)', textAlign: 'center' }}>{t(c.label)}</div>)}
        </div>
        {profiles.map((p) => (
          <div key={p.name} style={{ display: 'grid', gridTemplateColumns: cols, alignItems: 'stretch' }}>
            <div style={{ padding: '6px 12px', fontSize: 12.5, textTransform: 'capitalize', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', borderBottom: '1px solid var(--line)' }}>{p.name.replace(/_/g, ' ')}</div>
            {HM_COLS.map((c) => {
              const pass = c.ok(p)
              return (
                <div key={c.label} style={{ borderBottom: '1px solid var(--line)', borderLeft: '1px solid var(--line)', minHeight: 26, display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer' }}
                  onMouseMove={(e) => setTip({ x: e.clientX, y: e.clientY, title: `${p.name.replace(/_/g, ' ')} · ${t(c.label)}`, value: pass ? t('pass') : t('fail') })}
                  onMouseLeave={() => setTip(null)}>
                  <span style={{ width: '78%', height: 14, borderRadius: 3, background: pass ? 'var(--green)' : 'var(--clay)', opacity: inView ? (pass ? 0.85 : 0.7) : 0, transition: 'opacity .5s ease' }} />
                </div>
              )
            })}
          </div>
        ))}
      </div>
      {tip && <ChartTooltip x={tip.x} y={tip.y}><div style={{ fontWeight: 600, textTransform: 'capitalize' }}>{tip.title}</div><div style={{ opacity: 0.85 }}>{tip.value}</div></ChartTooltip>}
    </div>
  )
}

// ── Section 6: top candidates by drug-likeness score ─────────────────────
function TopCandidates({ profiles, avgLe }: { profiles: AdmetProfile[]; avgLe: Record<string, number> }) {
  const { t } = useT()
  const rows = [...profiles].sort((a, b) => b.dl - a.dl || a.name.localeCompare(b.name))
  const th = { padding: '9px 12px', textAlign: 'right' as const, fontFamily: 'var(--mono)', fontSize: 10, letterSpacing: '.05em', textTransform: 'uppercase' as const, color: 'var(--ink-faint)', borderBottom: '1px solid var(--line)', position: 'sticky' as const, top: 0, background: 'var(--paper-2)', whiteSpace: 'nowrap' as const }
  const td = { padding: '8px 12px', textAlign: 'right' as const, fontFamily: 'var(--mono)', fontSize: 12, borderBottom: '1px solid var(--line)', whiteSpace: 'nowrap' as const }
  return (
    <div style={{ border: '1px solid var(--line)', borderRadius: 14, overflow: 'auto', maxHeight: 560, background: 'var(--paper)' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
        <thead><tr>
          <th style={{ ...th, textAlign: 'left' }}>{t('Drug')}</th>
          <th style={{ ...th, textAlign: 'left', width: 130 }}>{t('DL score')}</th>
          {['MW', 'LogP', 'TPSA', 'ESOL', 'GI', 'BBB', 'Alerts', 'Avg LE'].map((h) => <th key={h} style={th}>{t(h)}</th>)}
        </tr></thead>
        <tbody>
          {rows.map((p) => (
            <tr key={p.name}>
              <td style={{ padding: '8px 12px', textTransform: 'capitalize', borderBottom: '1px solid var(--line)', whiteSpace: 'nowrap' }}>{p.name.replace(/_/g, ' ')}</td>
              <td style={{ padding: '8px 12px', borderBottom: '1px solid var(--line)' }}>
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
                  <span style={{ width: 70, height: 8, background: 'var(--paper-3)', borderRadius: 100, overflow: 'hidden' }}>
                    <span style={{ display: 'block', height: '100%', width: `${(p.dl / 5) * 100}%`, background: p.dl >= 4 ? 'var(--green)' : p.dl >= 3 ? 'var(--gold)' : 'var(--clay)', borderRadius: 100 }} />
                  </span>
                  <span style={{ fontFamily: 'var(--mono)', fontSize: 11 }}>{p.dl}/5</span>
                </span>
              </td>
              <td style={td}>{p.desc.mw}</td>
              <td style={td}>{p.desc.logp}</td>
              <td style={td}>{p.desc.tpsa}</td>
              <td style={td}>{p.esol}</td>
              <td style={{ ...td, color: p.gi === 'High' ? 'var(--green)' : 'var(--ink-soft)' }}>{p.gi}</td>
              <td style={{ ...td, color: p.bbb === 'Yes' ? 'var(--gold)' : 'var(--ink-faint)' }}>{p.bbb}</td>
              <td style={{ ...td, color: p.pains.length + p.brenk.length ? 'var(--clay)' : 'var(--ink-faint)' }}>{p.pains.length + p.brenk.length}</td>
              <td style={td}>{avgLe[p.name] != null ? avgLe[p.name].toFixed(3) : '-'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default function Admet() {
  const { t } = useT()
  const admet = useAdmet()
  const profiles = useAdmetProfiles()
  const drugs = useDrugs()
  const field = useField()
  const [q, setQ] = useState('')
  const [passOnly, setPassOnly] = useState(false)
  const [hov, setHov] = useState<string | null>(null)
  const [sel, setSel] = useState('celecoxib')

  const profs = profiles.data ?? []
  const selProf = profs.find((p) => p.name === sel) ?? profs[0]

  // average ligand efficiency per drug, over drug-like target rows
  const avgLe: Record<string, number> = {}
  if (field.data) {
    const acc: Record<string, number[]> = {}
    for (const pts of Object.values(field.data)) for (const p of pts) if (p.dl === 1 && p.le != null) (acc[p.name] ??= []).push(p.le)
    for (const [k, v] of Object.entries(acc)) avgLe[k] = v.reduce((a, b) => a + b, 0) / v.length
  }

  const score5 = profs.filter((p) => p.dl === 5).length
  const score4 = profs.filter((p) => p.dl >= 4).length

  // toxicity-risk table (per-drug, from the admet_predict model)
  const toxRows = (drugs.data ?? [])
    .map((d) => ({ drug: d, a: admet.data?.[d.name] }))
    .filter((r): r is { drug: Drug; a: AdmetRow } => !!r.a)
  const nPass = toxRows.filter((r) => r.a.pass).length
  const toxFiltered = toxRows
    .filter((r) => (!q || r.drug.name.toLowerCase().includes(q.toLowerCase())) && (!passOnly || r.a.pass))
    .sort((x, y) => x.drug.name.localeCompare(y.drug.name))
  const cellR = { padding: '9px 12px', textAlign: 'right' as const, fontFamily: 'var(--mono)', fontSize: 12, whiteSpace: 'nowrap' as const }

  return (
    <div className="wrap" style={{ padding: '56px 0' }}>
      <div className="eyebrow">{t('Tool 04')}</div>
      <h1 style={{ fontSize: 'clamp(34px,5vw,60px)', fontWeight: 380, marginTop: 12 }}>{t('ADMET Profiling')}</h1>
      <p style={{ color: 'var(--ink-soft)', maxWidth: 760, lineHeight: 1.65, margin: '14px 0 8px' }}>
        {t('Whether each drug looks safe and drug-like: rule-based filters, absorption prediction, structural alerts, and toxicity risks. All values are computational estimates from each molecule, not clinical results.')}
      </p>

      {!profiles.data ? <p className="mono" style={{ marginTop: 20 }}>{t('Loading ADMET profiles...')}</p> : (
        <>
          <div style={{ marginTop: 30 }}><H3>{t('1 · Drug-likeness filters')}</H3><Lede>{t('How many of the')} {profs.length} {t('drugs pass each rule-based drug-likeness filter.')}</Lede><FilterSummary profiles={profs} /></div>

          <div style={{ marginTop: 38 }}>
            <H3>{t('2 · Physicochemical radar')}</H3>
            <Lede>{t('Each descriptor normalised to its Lipinski/Veber limit. Inside the dashed green ring (1.0) satisfies the rule; spikes beyond it are liabilities.')}</Lede>
            <select value={sel} onChange={(e) => setSel(e.target.value)} style={{ fontFamily: 'var(--sans)', fontSize: 14, padding: '8px 14px', borderRadius: 12, border: '1px solid var(--line)', background: 'var(--paper)', color: 'var(--ink)', minWidth: 240, textTransform: 'capitalize', marginBottom: 14 }}>
              {[...profs].sort((a, b) => a.name.localeCompare(b.name)).map((p) => <option key={p.name} value={p.name}>{p.name}</option>)}
            </select>
            {selProf && (
              <div className="rstack" style={{ display: 'grid', gridTemplateColumns: 'minmax(0,440px) 1fr', gap: 28, alignItems: 'center' }}>
                <PhysChemRadar p={selProf} />
                <div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0,1fr))', gap: '10px 22px', maxWidth: 360 }}>
                    {[[t('Molecular weight'), `${selProf.desc.mw} Da`], ['LogP', `${selProf.desc.logp}`], ['TPSA', `${selProf.desc.tpsa} Å²`], [t('H-bond donors'), `${selProf.desc.hbd}`], [t('H-bond acceptors'), `${selProf.desc.hba}`], [t('Rotatable bonds'), `${selProf.desc.rot}`], ['ESOL (logS)', `${selProf.esol}`], [t('Drug-likeness'), `${selProf.dl}/5`]].map(([k, v]) => (
                      <div key={k}><div style={{ fontFamily: 'var(--mono)', fontSize: 9.5, letterSpacing: '.06em', textTransform: 'uppercase', color: 'var(--ink-faint)' }}>{k}</div><div style={{ fontSize: 15, marginTop: 2 }}>{v}</div></div>
                    ))}
                  </div>
                  <div style={{ display: 'flex', gap: 7, flexWrap: 'wrap', marginTop: 16 }}>
                    {([['Lipinski', selProf.lipinski], ['Veber', selProf.veber], ['Ghose', selProf.ghose], ['Egan', selProf.egan], [t('PAINS clean'), selProf.pains.length === 0]] as const).map(([label, ok]) => (
                      <span key={label} style={{ fontFamily: 'var(--mono)', fontSize: 10, letterSpacing: '.04em', textTransform: 'uppercase', borderRadius: 100, padding: '4px 10px', border: `1px solid ${ok ? 'var(--green)' : 'var(--clay)'}`, color: ok ? 'var(--green)' : 'var(--clay)' }}>{label}: {ok ? t('pass') : t('fail')}</span>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>

          <div style={{ marginTop: 38 }}><H3>{t('3 · BOILED-Egg absorption')}</H3><Lede>{t('Predicts gut (GI) absorption and blood-brain-barrier penetration from LogP and TPSA. The teal "white" is high GI absorption; the gold "yolk" is probable BBB permeation.')}</Lede><BoiledEgg profiles={profs} /></div>

          <div style={{ marginTop: 38 }}><H3>{t('4 · Structural alerts')}</H3><Lede>{t('PAINS and Brenk filters flag substructures linked to assay artefacts or chemical instability.')}</Lede><AlertsTable profiles={profs} /></div>

          <div style={{ marginTop: 38 }}><H3>{t('5 · Property heatmap')}</H3><Lede>{t('Pass/fail across eight criteria for every drug. Green is a pass, clay is a fail. Hover any cell.')}</Lede><PropertyHeatmap profiles={profs} /></div>

          <div style={{ marginTop: 38 }}>
            <H3>{t('6 · Top candidates by drug-likeness')}</H3>
            <Lede>{t('Ranked by drug-likeness score (filters passed, 0-5).')} <b>{score5}</b> {t('score a perfect 5/5 and')} <b>{score4}</b> {t('score 4 or more.')}</Lede>
            <TopCandidates profiles={profs} avgLe={avgLe} />
          </div>

          <div style={{ marginTop: 38 }}>
            <H3>{t('Toxicity risk')}</H3>
            <Lede>{t('Predicted hepatotoxicity, hERG and oral-bioavailability estimates per drug, with the overall safety pass used to filter candidates.')} {toxRows.length > 0 && <span className="mono" style={{ color: 'var(--ink-faint)' }}>{nPass} {t('of')} {toxRows.length} {t('pass.')}</span>}</Lede>
            <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'center', marginBottom: 14 }}>
              <input value={q} onChange={(e) => setQ(e.target.value)} placeholder={t('Search drug...')} style={{ fontFamily: 'var(--sans)', fontSize: 14, padding: '8px 14px', borderRadius: 100, border: '1px solid var(--line)', background: 'var(--paper)', color: 'var(--ink)', minWidth: 180 }} />
              <button onClick={() => setPassOnly((v) => !v)} style={{ fontFamily: 'var(--mono)', fontSize: 10.5, letterSpacing: '.06em', textTransform: 'uppercase', padding: '8px 13px', borderRadius: 100, cursor: 'pointer', border: '1px solid var(--line)', background: passOnly ? 'var(--green)' : 'var(--paper)', color: passOnly ? 'var(--paper)' : 'var(--ink-soft)' }}>{t('Passing only')}</button>
              <span className="mono" style={{ color: 'var(--ink-faint)' }}>{toxFiltered.length} {t('shown')}</span>
            </div>
            <div style={{ border: '1px solid var(--line)', borderRadius: 14, overflow: 'auto', maxHeight: 560, background: 'var(--paper)' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13.5 }}>
                <thead><tr>{[t('Drug'), 'Lipinski', t('Hepatotoxicity'), 'hERG', t('Bioavailability'), t('Overall')].map((h, i) => (
                  <th key={h} style={{ position: 'sticky', top: 0, zIndex: 1, background: 'var(--paper-2)', padding: '10px 12px', textAlign: i === 0 ? 'left' : 'right', fontFamily: 'var(--mono)', fontSize: 10, letterSpacing: '.08em', textTransform: 'uppercase', color: 'var(--ink-faint)', borderBottom: '1px solid var(--line)', whiteSpace: 'nowrap' }}>{h}</th>
                ))}</tr></thead>
                <tbody>
                  {toxFiltered.map(({ drug, a }) => {
                    const hb = band(a.hepatotox), he = band(a.herg)
                    return (
                      <tr key={drug.name} onMouseEnter={() => setHov(drug.name)} onMouseLeave={() => setHov(null)} style={{ background: hov === drug.name ? 'var(--paper-2)' : 'transparent', borderBottom: '1px solid var(--line)' }}>
                        <td style={{ padding: '9px 12px' }}><span style={{ display: 'inline-flex', alignItems: 'center', gap: 9 }}><span style={{ width: 9, height: 9, borderRadius: '50%', background: bucketOf(drug).color, flex: 'none' }} /><span style={{ textTransform: 'capitalize' }}>{drug.name.replace(/_/g, ' ')}</span></span></td>
                        <td style={{ ...cellR, color: a.lipinski ? 'var(--green)' : 'var(--clay)' }}>{a.lipinski ? t('pass') : t('fail')}</td>
                        <td style={{ ...cellR, color: hb.color }}>{t(hb.label)} ({a.hepatotox.toFixed(2)})</td>
                        <td style={{ ...cellR, color: he.color }}>{t(he.label)} ({a.herg.toFixed(2)})</td>
                        <td style={{ ...cellR, color: 'var(--ink-soft)' }}>{Math.round(a.bioavail * 100)}%</td>
                        <td style={{ ...cellR, color: a.pass ? 'var(--green)' : 'var(--clay)' }}>{a.pass ? t('pass') : t('flag')}</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
