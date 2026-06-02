import { useState, type ReactNode, type CSSProperties } from 'react'
import type { FieldPoint } from '../data/types'
import { bucketOf } from '../lib/buckets'

type Col = 'vina' | 'le' | 'mw' | 'name'

const cell = (color: string, align: 'left' | 'right', mono?: boolean): CSSProperties => ({
  padding: '9px 12px', color, textAlign: align, fontFamily: mono ? 'var(--mono)' : undefined, whiteSpace: 'nowrap',
})

function Pill({ children, color }: { children: ReactNode; color: string }) {
  return (
    <span style={{ fontFamily: 'var(--mono)', fontSize: 9, letterSpacing: '.06em', textTransform: 'uppercase', border: `1px solid ${color}`, color, borderRadius: 100, padding: '2px 7px' }}>
      {children}
    </span>
  )
}

export function DrugTable({ points, onSelect, selected }: { points: FieldPoint[]; onSelect: (p: FieldPoint) => void; selected?: string }) {
  const [col, setCol] = useState<Col>('vina')
  const [dir, setDir] = useState<1 | -1>(1)
  const [hov, setHov] = useState<string | null>(null)
  const sorted = [...points].sort((a, b) => {
    const d = col === 'name' ? a.name.localeCompare(b.name) : col === 'vina' ? a.vina - b.vina : col === 'le' ? (a.le ?? 0) - (b.le ?? 0) : a.mw - b.mw
    return d * dir
  })
  const click = (c: Col) => {
    if (c === col) setDir((x) => (x === 1 ? -1 : 1))
    else { setCol(c); setDir(c === 'le' ? -1 : 1) }
  }
  const th = (label: string, c?: Col, right?: boolean) => (
    <th
      onClick={c ? () => click(c) : undefined}
      style={{ position: 'sticky', top: 0, zIndex: 1, background: 'var(--paper-2)', padding: '10px 12px', textAlign: right ? 'right' : 'left', fontFamily: 'var(--mono)', fontSize: 10, letterSpacing: '.08em', textTransform: 'uppercase', color: 'var(--ink-faint)', cursor: c ? 'pointer' : 'default', borderBottom: '1px solid var(--line)', whiteSpace: 'nowrap', userSelect: 'none' }}
    >
      {label}{c === col ? (dir === 1 ? ' ↑' : ' ↓') : ''}
    </th>
  )
  return (
    <div style={{ border: '1px solid var(--line)', borderRadius: 14, overflow: 'auto', maxHeight: 640, background: 'var(--paper)' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13.5 }}>
        <thead>
          <tr>{th('#')}{th('Drug', 'name')}{th('MW', 'mw', true)}{th('Vina', 'vina', true)}{th('Lig. eff.', 'le', true)}{th('Drug-like')}{th('ADMET')}</tr>
        </thead>
        <tbody>
          {sorted.map((p, i) => {
            const b = bucketOf(p)
            const bg = selected === p.name ? 'var(--paper-3)' : hov === p.name ? 'var(--paper-2)' : 'transparent'
            return (
              <tr key={p.name} onClick={() => onSelect(p)} onMouseEnter={() => setHov(p.name)} onMouseLeave={() => setHov(null)} style={{ cursor: 'pointer', background: bg, borderBottom: '1px solid var(--line)' }}>
                <td style={cell('var(--ink-faint)', 'left', true)}>{i + 1}</td>
                <td style={{ padding: '9px 12px' }}>
                  <span style={{ display: 'inline-flex', alignItems: 'center', gap: 9 }}>
                    <span style={{ width: 9, height: 9, borderRadius: '50%', background: b.color, flex: 'none' }} />
                    <span style={{ textTransform: 'capitalize' }}>{p.name.replace(/_/g, ' ')}</span>
                  </span>
                </td>
                <td style={cell('var(--ink-soft)', 'right', true)}>{Math.round(p.mw)}</td>
                <td style={cell('var(--ink)', 'right', true)}>{p.vina}</td>
                <td style={cell('var(--ink-soft)', 'right', true)}>{p.le !== null ? p.le.toFixed(3) : '-'}</td>
                <td style={{ padding: '9px 12px' }}>{p.dl ? <Pill color="var(--green)">yes</Pill> : <span style={{ color: 'var(--ink-faint)', fontFamily: 'var(--mono)', fontSize: 10 }}>no</span>}</td>
                <td style={{ padding: '9px 12px' }}>{p.admet ? <Pill color="var(--green)">pass</Pill> : <Pill color="var(--clay)">flag</Pill>}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
