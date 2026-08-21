import { useState, type ReactNode } from 'react'
import type { FieldPoint } from '../data/types'
import { bucketOf } from '../lib/buckets'
import { ChartTooltip } from '../components/ChartTooltip'
import { useInView } from '../lib/anim'
import { useT } from '../i18n'

type SortKey = 'binding' | 'efficiency'

function Tag({ children, color }: { children: ReactNode; color?: string }) {
  return (
    <span style={{ fontFamily: 'var(--mono)', fontSize: 9, letterSpacing: '.06em', textTransform: 'uppercase', border: '1px solid var(--line)', borderRadius: 100, padding: '2px 7px', color: color ?? 'var(--ink-faint)', whiteSpace: 'nowrap' }}>
      {children}
    </span>
  )
}

export function CandidateBoard({ points }: { points: FieldPoint[] }) {
  const { t } = useT()
  const [sortKey, setSortKey] = useState<SortKey>('binding')
  const [hover, setHover] = useState<string | null>(null)
  const [tip, setTip] = useState<{ x: number; y: number; name: string; metric: string; cls: string } | null>(null)
  const [boardRef, inView] = useInView<HTMLDivElement>()
  const sorted = [...points].sort((a, b) => (sortKey === 'binding' ? a.vina - b.vina : (b.le ?? 0) - (a.le ?? 0)))
  const vals = sorted.map((p) => (sortKey === 'binding' ? -p.vina : p.le ?? 0))
  const max = Math.max(...vals)
  const min = Math.min(...vals)
  const pct = (p: FieldPoint) => {
    const v = sortKey === 'binding' ? -p.vina : p.le ?? 0
    return max === min ? 100 : 10 + ((v - min) / (max - min)) * 90
  }
  return (
    <div ref={boardRef}>
      <div style={{ display: 'inline-flex', border: '1px solid var(--line)', borderRadius: 100, overflow: 'hidden', fontFamily: 'var(--mono)', fontSize: 10.5, letterSpacing: '.06em', textTransform: 'uppercase', marginBottom: 16 }}>
        {(['binding', 'efficiency'] as const).map((k) => (
          <span key={k} onClick={() => setSortKey(k)} style={{ padding: '8px 14px', cursor: 'pointer', color: sortKey === k ? 'var(--paper)' : 'var(--ink-faint)', background: sortKey === k ? 'var(--green)' : 'transparent' }}>
            {k === 'binding' ? t('By binding') : t('By efficiency')}
          </span>
        ))}
      </div>
      <div style={{ border: '1px solid var(--line)', borderRadius: 14, overflow: 'hidden', maxHeight: 620, overflowY: 'auto', background: 'var(--paper)' }}>
        {sorted.map((p, i) => {
          const b = bucketOf(p)
          return (
            <div
              key={p.name}
              onMouseEnter={() => setHover(p.name)}
              onMouseMove={(e) => setTip({ x: e.clientX, y: e.clientY, name: p.name.replace(/_/g, ' '), metric: sortKey === 'binding' ? `Vina ${p.vina} kcal/mol` : `${t('Ligand efficiency')} ${p.le != null ? p.le.toFixed(3) : t('n/a')}`, cls: t(b.label) })}
              onMouseLeave={() => { setHover(null); setTip(null) }}
              style={{ display: 'grid', gridTemplateColumns: '30px 1fr 116px', alignItems: 'center', gap: 14, padding: '11px 16px', borderBottom: i < sorted.length - 1 ? '1px solid var(--line)' : 'none', background: hover === p.name ? 'var(--paper-2)' : 'transparent', opacity: p.dl ? 1 : 0.6 }}
            >
              <div style={{ fontFamily: 'var(--mono)', fontSize: 12, color: 'var(--ink-faint)' }}>{i + 1}</div>
              <div style={{ minWidth: 0 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                  <span style={{ fontFamily: 'var(--serif)', fontSize: 17, textTransform: 'capitalize' }}>{p.name.replace(/_/g, ' ')}</span>
                  {p.dl === 1 ? <Tag color="var(--green)">{t('drug-like')}</Tag> : <Tag>{t('outside drug-like range')}</Tag>}
                  {p.name.toLowerCase() === 'sofosbuvir' && <Tag color="var(--ink-soft)">{t('control')}</Tag>}
                  {!p.admet && <Tag color="var(--clay)">{t('ADMET flag')}</Tag>}
                </div>
                <div style={{ height: 8, background: 'var(--paper-3)', borderRadius: 100, marginTop: 7, overflow: 'hidden' }}>
                  <div className="bar" style={{ height: '100%', width: inView ? `${pct(p)}%` : '0%', background: b.color, borderRadius: 100, transitionDelay: `${Math.min(i * 10, 500)}ms` }} />
                </div>
              </div>
              <div style={{ fontFamily: 'var(--mono)', fontSize: 12, color: 'var(--ink)', textAlign: 'right' }}>
                {sortKey === 'binding' ? p.vina : p.le !== null ? p.le.toFixed(3) : t('n/a')}
                <div style={{ fontSize: 9, color: 'var(--ink-faint)' }}>{sortKey === 'binding' ? 'kcal/mol' : t('per atom')}</div>
              </div>
            </div>
          )
        })}
      </div>
      {tip && (
        <ChartTooltip x={tip.x} y={tip.y}>
          <div style={{ fontWeight: 600, textTransform: 'capitalize' }}>{tip.name}</div>
          <div style={{ opacity: 0.9 }}>{tip.metric}</div>
          <div style={{ opacity: 0.7 }}>{tip.cls}</div>
        </ChartTooltip>
      )}
    </div>
  )
}
