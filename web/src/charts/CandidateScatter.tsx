import { useState } from 'react'
import { scaleLinear } from '@visx/scale'
import type { FieldPoint } from '../data/types'
import { bucketOf, insight, AXIS } from '../lib/buckets'
import { useRegister } from '../state/register'

const W = 920
const H = 560
const M = { top: 28, right: 30, bottom: 56, left: 60 }
const IW = W - M.left - M.right
const IH = H - M.top - M.bottom
const rad = (ha: number) => 5 + (ha / 79) * 15

export function CandidateScatter({ points }: { points: FieldPoint[] }) {
  const { reg } = useRegister()
  const [hover, setHover] = useState<FieldPoint | null>(null)
  const [pos, setPos] = useState({ x: 0, y: 0, w: 1, h: 1 })

  if (!points.length) return null
  const vinas = points.map((p) => p.vina)
  const les = points.map((p) => p.le ?? 0)
  const x = scaleLinear({ domain: [Math.max(...vinas) + 0.2, Math.min(...vinas) - 0.2], range: [0, IW] })
  const y = scaleLinear({ domain: [Math.max(0, Math.min(...les) - 0.02), Math.max(...les) + 0.02], range: [IH, 0] })
  const a = AXIS[reg]
  const sorted = [...points].sort((p, q) => q.ha - p.ha) // big drawn first, small on top
  const b = hover ? bucketOf(hover) : null
  const tipLeft = pos.x + 246 > pos.w ? pos.x - 246 : pos.x + 16
  const tipTop = pos.y + 230 > pos.h ? Math.max(8, pos.y - 220) : pos.y + 10

  return (
    <div
      style={{ position: 'relative', border: '1px solid var(--line)', borderRadius: 18, overflow: 'hidden', background: 'radial-gradient(120% 90% at 30% 10%, #fbf8ef 0%, #efe9da 60%, #e7e0cf 100%)' }}
      onPointerMove={(e) => { const r = e.currentTarget.getBoundingClientRect(); setPos({ x: e.clientX - r.left, y: e.clientY - r.top, w: r.width, h: r.height }) }}
      onPointerLeave={() => setHover(null)}
    >
      <svg viewBox={`0 0 ${W} ${H}`} width="100%" style={{ display: 'block' }}>
        <g transform={`translate(${M.left},${M.top})`}>
          <line x1={0} y1={IH} x2={IW} y2={IH} stroke="#cdc3ad" strokeWidth={1} />
          <line x1={0} y1={0} x2={0} y2={IH} stroke="#cdc3ad" strokeWidth={1} />
          {sorted.map((p, i) => (
            <circle
              key={p.name}
              className="dot"
              cx={x(p.vina)}
              cy={y(p.le ?? 0)}
              r={rad(p.ha)}
              fill={bucketOf(p).color}
              fillOpacity={p.admet ? 0.9 : 0.38}
              stroke={p.dl ? '#2E7D5B' : 'transparent'}
              strokeWidth={p.dl ? 1.8 : 0}
              style={{ cursor: 'pointer', animationDelay: `${Math.min(i * 6, 500)}ms` }}
              onPointerEnter={() => setHover(p)}
            />
          ))}
        </g>
        <text x={M.left + IW / 2} y={H - 14} textAnchor="middle" fontFamily="var(--mono)" fontSize={11} fill="#8A8273" letterSpacing="0.06em">
          {a.x} {reg === 'plain' ? '(weaker to stronger)' : '(stronger to the right)'}
        </text>
        <text transform={`translate(18,${M.top + IH / 2}) rotate(-90)`} textAnchor="middle" fontFamily="var(--mono)" fontSize={11} fill="#8A8273" letterSpacing="0.06em">
          {a.y} (higher is better)
        </text>
      </svg>
      {hover && b && (
        <div style={{ position: 'absolute', left: tipLeft, top: tipTop, width: 230, background: 'var(--ink)', color: 'var(--paper)', borderRadius: 12, padding: '14px 15px', boxShadow: '0 18px 40px rgba(28,26,23,.28)', pointerEvents: 'none', zIndex: 5 }}>
          <div style={{ fontFamily: 'var(--serif)', fontSize: 19, textTransform: 'capitalize' }}>{hover.name.replace(/_/g, ' ')}</div>
          <div style={{ fontFamily: 'var(--mono)', fontSize: 9.5, letterSpacing: '.08em', textTransform: 'uppercase', color: b.color, marginTop: 2 }}>{b.label}</div>
          <div style={{ fontSize: 12.5, color: '#e8e0d2', marginTop: 8 }}>Approved for: <b style={{ color: '#fff' }}>{hover.indication}</b></div>
          <Row k="Binding (Vina)" v={`${hover.vina} kcal/mol`} />
          <Row k="Efficiency / atom" v={hover.le !== null ? hover.le.toFixed(3) : 'n/a'} />
          <Row k="Size" v={`${Math.round(hover.mw)} Da, ${hover.ha} atoms`} />
          <Row k="Drug-like, Safe" v={`${hover.dl ? 'yes' : 'no'}, ${hover.admet ? 'pass' : 'flag'}`} />
          <div style={{ fontSize: 13, lineHeight: 1.5, marginTop: 10, borderTop: '1px solid #3a352d', paddingTop: 9, color: '#f4f0e6' }}>{insight(hover)}</div>
        </div>
      )}
    </div>
  )
}

function Row({ k, v }: { k: string; v: string }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', fontFamily: 'var(--mono)', fontSize: 11, color: '#cdbfae', marginTop: 5 }}>
      <span>{k}</span><b style={{ color: '#fff', fontWeight: 500 }}>{v}</b>
    </div>
  )
}
