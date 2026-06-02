import { scaleLinear } from '@visx/scale'

export interface ChartLine { label: string; color: string; pts: [number, number][] }

const W = 900
const H = 320
const M = { top: 16, right: 22, bottom: 40, left: 52 }
const IW = W - M.left - M.right
const IH = H - M.top - M.bottom

export function MultiLineChart({ lines, xLabel, yLabel, yMin }: { lines: ChartLine[]; xLabel: string; yLabel: string; yMin?: number }) {
  const all = lines.flatMap((l) => l.pts)
  if (!all.length) return <div className="mono" style={{ color: 'var(--ink-faint)', padding: 20 }}>No data.</div>
  const xs = all.map((p) => p[0])
  const ys = all.map((p) => p[1])
  const x = scaleLinear({ domain: [Math.min(...xs), Math.max(...xs)], range: [0, IW] })
  const y = scaleLinear({ domain: [yMin ?? Math.min(...ys), Math.max(...ys)], range: [IH, 0], nice: true })
  const path = (pts: [number, number][]) => pts.map((p, i) => `${i ? 'L' : 'M'}${x(p[0]).toFixed(1)} ${y(p[1]).toFixed(1)}`).join(' ')
  return (
    <div style={{ border: '1px solid var(--line)', borderRadius: 14, background: 'var(--paper)', padding: '14px 16px 8px' }}>
      <svg viewBox={`0 0 ${W} ${H}`} width="100%" style={{ display: 'block' }}>
        <g transform={`translate(${M.left},${M.top})`}>
          {y.ticks(4).map((t, i) => (
            <g key={`y${i}`}>
              <line x1={0} y1={y(t)} x2={IW} y2={y(t)} stroke="var(--line)" strokeWidth={0.5} opacity={0.7} />
              <text x={-8} y={y(t)} textAnchor="end" dominantBaseline="middle" fontFamily="var(--mono)" fontSize={9} fill="var(--ink-faint)">{t}</text>
            </g>
          ))}
          {x.ticks(6).map((t, i) => (
            <text key={`x${i}`} x={x(t)} y={IH + 15} textAnchor="middle" fontFamily="var(--mono)" fontSize={9} fill="var(--ink-faint)">{t}</text>
          ))}
          <line x1={0} y1={IH} x2={IW} y2={IH} stroke="var(--ink-faint)" strokeWidth={0.8} />
          {lines.map((l) => (l.pts.length ? <path key={l.label} d={path(l.pts)} fill="none" stroke={l.color} strokeWidth={1.6} strokeLinejoin="round" /> : null))}
        </g>
        <text x={M.left + IW / 2} y={H - 4} textAnchor="middle" fontFamily="var(--mono)" fontSize={10} fill="var(--ink-soft)">{xLabel}</text>
        <text transform={`translate(13,${M.top + IH / 2}) rotate(-90)`} textAnchor="middle" fontFamily="var(--mono)" fontSize={10} fill="var(--ink-soft)">{yLabel}</text>
      </svg>
      <div style={{ display: 'flex', gap: 18, flexWrap: 'wrap', marginTop: 4, paddingLeft: M.left / 1.6 }}>
        {lines.map((l) => (
          <span key={l.label} style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 12, color: l.pts.length ? 'var(--ink-soft)' : 'var(--ink-faint)' }}>
            <span style={{ width: 16, height: 3, background: l.color, borderRadius: 2, opacity: l.pts.length ? 1 : 0.4 }} />
            {l.label}{l.pts.length ? '' : ' (no stable pose)'}
          </span>
        ))}
      </div>
    </div>
  )
}
