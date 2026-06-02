import { useState } from 'react'
import { ChartTooltip } from './ChartTooltip'

type Axis = { label: string; value: number }

/** Lightweight polar radar (regular polygon). Values are clamped to 0..1. Hover a vertex for its value. */
export function RadarChart({ axes, color = 'var(--green)' }: { axes: Axis[]; color?: string }) {
  const [tip, setTip] = useState<{ x: number; y: number; title: string; value: string } | null>(null)
  const W = 480
  const H = 360
  const cx = W / 2
  const cy = H / 2
  const R = 112
  const n = axes.length || 1
  const ang = (i: number) => (i / n) * Math.PI * 2 - Math.PI / 2
  const at = (i: number, r: number): [number, number] => [cx + r * Math.cos(ang(i)), cy + r * Math.sin(ang(i))]
  const clamp = (v: number) => Math.max(0, Math.min(1, v))
  const rings = [0.2, 0.4, 0.6, 0.8, 1]
  const ringPts = (f: number) => axes.map((_, i) => at(i, R * f).join(',')).join(' ')
  const dataPts = axes.map((a, i) => at(i, R * clamp(a.value)).join(',')).join(' ')

  return (
    <>
      <svg viewBox={`0 0 ${W} ${H}`} width="100%" style={{ overflow: 'visible', display: 'block' }} role="img" aria-label="ADMET safety radar">
        {rings.map((f) => (
          <polygon key={f} points={ringPts(f)} fill="none" stroke="var(--line)" strokeWidth={1} />
        ))}
        {axes.map((_, i) => {
          const [x, y] = at(i, R)
          return <line key={i} x1={cx} y1={cy} x2={x} y2={y} stroke="var(--line)" strokeWidth={1} />
        })}
        <polygon points={dataPts} fill={color} fillOpacity={0.16} stroke={color} strokeWidth={2} strokeLinejoin="round" />
        {rings.map((f) => {
          const [x, y] = at(0, R * f)
          return (
            <text key={f} x={x + 5} y={y} fontSize={9} fontFamily="var(--mono)" fill="var(--ink-faint)" dominantBaseline="middle">
              {f}
            </text>
          )
        })}
        {axes.map((a, i) => {
          const [x, y] = at(i, R + 16)
          const anchor = Math.abs(x - cx) < 6 ? 'middle' : x > cx ? 'start' : 'end'
          return (
            <text key={a.label} x={x} y={y} fontSize={11} fill="var(--ink-soft)" textAnchor={anchor} dominantBaseline="middle">
              {a.label}
            </text>
          )
        })}
        <text x={cx - 5} y={cy + 4} fontSize={9} fontFamily="var(--mono)" fill="var(--ink-faint)" textAnchor="end">0</text>
        {axes.map((a, i) => {
          const [x, y] = at(i, R * clamp(a.value))
          return (
            <g
              key={a.label}
              style={{ cursor: 'pointer' }}
              onMouseMove={(e) => setTip({ x: e.clientX, y: e.clientY, title: a.label, value: a.value.toFixed(2) })}
              onMouseLeave={() => setTip(null)}
            >
              <circle cx={x} cy={y} r={12} fill="transparent" />
              <circle cx={x} cy={y} r={3.5} fill={color} />
            </g>
          )
        })}
      </svg>
      {tip && (
        <ChartTooltip x={tip.x} y={tip.y}>
          <div style={{ fontWeight: 600 }}>{tip.title}</div>
          <div style={{ opacity: 0.85 }}>{tip.value}</div>
        </ChartTooltip>
      )}
    </>
  )
}
