import { useState } from 'react'
import { ChartTooltip } from './ChartTooltip'
import { useInView } from '../lib/anim'
import { useT } from '../i18n'

function gradeColor(g: number) {
  const t = (Math.max(1, Math.min(9, g)) - 1) / 8
  const l = (a: number, b: number) => Math.round(a + (b - a) * t)
  // pale (variable) -> clay (conserved)
  return `rgb(${l(222, 168)},${l(214, 73)},${l(196, 43)})`
}

export function ConservationTrack({ grades, keyResidues }: { grades: Record<string, number>; keyResidues: number[] }) {
  const { t } = useT()
  const [tip, setTip] = useState<{ cx: number; cy: number; i: number; resnum: number; grade: number } | null>(null)
  const [ref, inView] = useInView<SVGSVGElement>()
  const entries = Object.entries(grades)
    .map(([k, v]) => [parseInt(k, 10), v] as [number, number])
    .sort((a, b) => a[0] - b[0])
  const n = entries.length
  if (!n) return null
  const W = 920
  const H = 44
  const bw = W / n
  const idxOf = (resnum: number) => entries.findIndex((e) => e[0] === resnum)
  const ticks = [1, 150, 300, 450, 600, 750, entries[n - 1][0]]
  const keySet = new Set(keyResidues)
  const grLabel = (g: number) => (g <= 3 ? t('variable') : g >= 7 ? t('conserved') : t('intermediate'))
  return (
    <div style={{ border: '1px solid var(--line)', borderRadius: 14, background: 'var(--paper)', padding: '16px 16px 10px' }}>
      <svg ref={ref} viewBox={`0 0 ${W} ${H + 34}`} width="100%" style={{ display: 'block' }}>
        {entries.map(([resnum, g], i) => (
          <rect key={resnum} x={i * bw} y={0} width={bw + 0.6} height={H} fill={gradeColor(g)} className="grow-y" style={{ transform: inView ? 'scaleY(1)' : 'scaleY(0)', transitionDelay: `${Math.round((i / n) * 450)}ms` }} />
        ))}
        {keyResidues.map((rn) => {
          const i = idxOf(rn)
          if (i < 0) return null
          const cx = i * bw + bw / 2
          return <polygon key={rn} points={`${cx},${H + 1} ${cx - 4},${H + 9} ${cx + 4},${H + 9}`} fill="var(--ink)" />
        })}
        {ticks.map((t) => {
          const i = idxOf(t)
          const cx = i >= 0 ? i * bw + bw / 2 : (t / entries[n - 1][0]) * W
          return <text key={t} x={cx} y={H + 26} textAnchor="middle" fontFamily="var(--mono)" fontSize={9} fill="var(--ink-faint)">{t}</text>
        })}
        {tip && <rect x={tip.i * bw} y={0} width={Math.max(1.5, bw)} height={H} fill="none" stroke="var(--ink)" strokeWidth={1.4} />}
        <rect
          x={0}
          y={0}
          width={W}
          height={H}
          fill="transparent"
          style={{ cursor: 'crosshair' }}
          onMouseMove={(e) => {
            const r = e.currentTarget.getBoundingClientRect()
            const fx = Math.max(0, Math.min(0.9999, (e.clientX - r.left) / r.width))
            const i = Math.min(n - 1, Math.max(0, Math.floor(fx * n)))
            const [resnum, grade] = entries[i]
            setTip({ cx: e.clientX, cy: e.clientY, i, resnum, grade })
          }}
          onMouseLeave={() => setTip(null)}
        />
      </svg>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginTop: 8, fontFamily: 'var(--mono)', fontSize: 10, letterSpacing: '.06em', textTransform: 'uppercase', color: 'var(--ink-faint)' }}>
        <span>{t('Variable')}</span>
        <span style={{ flex: 1, maxWidth: 200, height: 8, borderRadius: 100, background: `linear-gradient(90deg, ${gradeColor(1)}, ${gradeColor(5)}, ${gradeColor(9)})` }} />
        <span>{t('Conserved')}</span>
        <span style={{ marginLeft: 16, color: 'var(--ink-soft)', textTransform: 'none', letterSpacing: 0 }}>▲ {t('catalytic residue')}</span>
      </div>
      {tip && (
        <ChartTooltip x={tip.cx} y={tip.cy}>
          <div style={{ fontWeight: 600 }}>{t('Residue')} {tip.resnum}</div>
          <div style={{ opacity: 0.9 }}>{t('Grade')} {tip.grade}/9 ({grLabel(tip.grade)})</div>
          {keySet.has(tip.resnum) && <div style={{ color: '#e0a98f' }}>{t('Catalytic residue')}</div>}
        </ChartTooltip>
      )}
    </div>
  )
}
