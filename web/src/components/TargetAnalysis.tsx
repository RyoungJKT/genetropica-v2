import { useState } from 'react'
import type { FieldPoint } from '../data/types'
import { ChartTooltip } from './ChartTooltip'
import { useInView, useCountUp } from '../lib/anim'

function StatCard({ label, value, highlight, active }: { label: string; value: number; highlight?: boolean; active: boolean }) {
  const n = useCountUp(value, active)
  return (
    <div style={{ border: `1px solid ${highlight ? 'var(--green)' : 'var(--line)'}`, borderRadius: 14, padding: '16px 18px', background: 'var(--paper)' }}>
      <div style={{ fontFamily: 'var(--mono)', fontSize: 10, letterSpacing: '.08em', textTransform: 'uppercase', color: 'var(--ink-faint)' }}>{label}</div>
      <div style={{ fontSize: 38, fontWeight: 380, marginTop: 6, lineHeight: 1 }}>{n}</div>
    </div>
  )
}

/** Per-target overview: counts, ligand-efficiency distribution, and the top candidates by efficiency. */
export function TargetAnalysis({ points, targetName, shown }: { points: FieldPoint[]; targetName: string; shown: number }) {
  const [tip, setTip] = useState<{ x: number; y: number; title: string; value: string } | null>(null)
  const [secRef, inView] = useInView<HTMLElement>()
  const dl = points.filter((p) => p.dl === 1)
  const admetSafe = points.filter((p) => p.dl === 1 && p.admet === 1).length
  const le = dl.map((p) => p.le).filter((v): v is number => v != null)
  const top10 = [...dl].filter((p) => p.le != null).sort((a, b) => (b.le ?? 0) - (a.le ?? 0)).slice(0, 10)

  // Histogram of ligand efficiency over drug-like candidates.
  const lo = le.length ? Math.min(...le) : 0
  const hi = le.length ? Math.max(...le) : 1
  const NB = 12
  const span = hi - lo || 1
  const counts = new Array(NB).fill(0)
  for (const v of le) {
    const idx = Math.max(0, Math.min(NB - 1, Math.floor(((v - lo) / span) * NB)))
    counts[idx]++
  }
  const maxCount = Math.max(1, ...counts)

  const HW = 460
  const HH = 220
  const mL = 34
  const mB = 36
  const mT = 8
  const mR = 10
  const iw = HW - mL - mR
  const ih = HH - mT - mB
  const xOf = (v: number) => mL + ((v - lo) / span) * iw
  const yTicks = Array.from(new Set([0, Math.ceil(maxCount / 2), maxCount]))

  const topMax = top10.reduce((m, p) => Math.max(m, p.le ?? 0), 0) || 1

  return (
    <section ref={secRef} style={{ margin: '8px 0 4px' }}>
      <h2 style={{ fontSize: 26, fontWeight: 380 }}>Target: {targetName}</h2>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 14, marginTop: 16 }}>
        <StatCard label="Total screened" value={points.length} highlight active={inView} />
        <StatCard label="Drug-like (MW 250-600)" value={dl.length} active={inView} />
        <StatCard label="ADMET-safe drug-like" value={admetSafe} active={inView} />
        <StatCard label="Showing" value={shown} active={inView} />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 28, marginTop: 26 }}>
        <div>
          <h3 style={{ fontSize: 15, marginBottom: 10 }}>Ligand-Efficiency Distribution (drug-like)</h3>
          <svg viewBox={`0 0 ${HW} ${HH}`} width="100%" style={{ display: 'block' }}>
            {yTicks.map((t) => {
              const y = mT + ih - (t / maxCount) * ih
              return (
                <g key={t}>
                  <line x1={mL} y1={y} x2={HW - mR} y2={y} stroke="var(--line)" strokeWidth={1} />
                  <text x={mL - 6} y={y} fontSize={9} fontFamily="var(--mono)" fill="var(--ink-faint)" textAnchor="end" dominantBaseline="middle">{t}</text>
                </g>
              )
            })}
            {counts.map((c, i) => {
              const x = mL + (i / NB) * iw
              const w = iw / NB
              const h = (c / maxCount) * ih
              const bLo = lo + (i / NB) * span
              const bHi = lo + ((i + 1) / NB) * span
              return (
                <g
                  key={i}
                  style={{ cursor: 'pointer' }}
                  onMouseMove={(e) => setTip({ x: e.clientX, y: e.clientY, title: `LE ${bLo.toFixed(3)} to ${bHi.toFixed(3)}`, value: `${c} drug${c === 1 ? '' : 's'}` })}
                  onMouseLeave={() => setTip(null)}
                >
                  <rect x={x} y={mT} width={w} height={ih} fill="transparent" />
                  <rect
                    x={x + 0.5}
                    y={mT + ih - h}
                    width={Math.max(1, w - 1)}
                    height={h}
                    fill="var(--green)"
                    className="grow-y"
                    style={{ transform: inView ? 'scaleY(1)' : 'scaleY(0)', transitionDelay: `${i * 25}ms` }}
                  />
                </g>
              )
            })}
            {[lo, (lo + hi) / 2, hi].map((v, i) => (
              <text key={i} x={xOf(v)} y={HH - 14} fontSize={9} fontFamily="var(--mono)" fill="var(--ink-faint)" textAnchor="middle">{v.toFixed(2)}</text>
            ))}
            <text x={mL + iw / 2} y={HH - 1} fontSize={10} fill="var(--ink-soft)" textAnchor="middle">Ligand Efficiency</text>
          </svg>
        </div>

        <div>
          <h3 style={{ fontSize: 15, marginBottom: 10 }}>Top 10 Drug-like Candidates by Ligand Efficiency</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 7 }}>
            {top10.map((p, idx) => (
              <div
                key={p.name}
                style={{ display: 'grid', gridTemplateColumns: '110px 1fr 42px', gap: 8, alignItems: 'center', cursor: 'pointer' }}
                onMouseMove={(e) => setTip({ x: e.clientX, y: e.clientY, title: p.name.replace(/_/g, ' '), value: `Ligand efficiency ${(p.le ?? 0).toFixed(3)}` })}
                onMouseLeave={() => setTip(null)}
              >
                <span style={{ fontSize: 12, color: 'var(--ink-soft)', textTransform: 'capitalize', textAlign: 'right', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{p.name.replace(/_/g, ' ')}</span>
                <div style={{ background: 'var(--paper-3)', borderRadius: 4, height: 14, overflow: 'hidden' }}>
                  <div className="bar" style={{ width: inView ? `${((p.le ?? 0) / topMax) * 100}%` : '0%', height: '100%', background: 'var(--green)', borderRadius: 4, transitionDelay: `${idx * 35}ms` }} />
                </div>
                <span style={{ fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--ink)' }}>{(p.le ?? 0).toFixed(3)}</span>
              </div>
            ))}
            {!top10.length && <p style={{ fontSize: 13, color: 'var(--ink-faint)' }}>No drug-like candidates with a ligand-efficiency value.</p>}
          </div>
        </div>
      </div>
      {tip && (
        <ChartTooltip x={tip.x} y={tip.y}>
          <div style={{ fontWeight: 600 }}>{tip.title}</div>
          <div style={{ opacity: 0.85 }}>{tip.value}</div>
        </ChartTooltip>
      )}
    </section>
  )
}
