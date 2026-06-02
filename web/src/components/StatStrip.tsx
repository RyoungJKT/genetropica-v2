import { useEffect, useRef, useState } from 'react'
import { useInView, useReducedMotion } from 'framer-motion'

function CountUp({ to }: { to: number }) {
  const ref = useRef<HTMLDivElement>(null)
  const inView = useInView(ref, { once: true, margin: '-10% 0px' })
  const reduce = useReducedMotion()
  const [n, setN] = useState(reduce ? to : 0)
  useEffect(() => {
    if (!inView || reduce) {
      setN(to)
      return
    }
    let raf = 0
    const t0 = performance.now()
    const dur = 1300
    const tick = (t: number) => {
      const p = Math.min(1, (t - t0) / dur)
      setN(Math.round(to * (1 - Math.pow(1 - p, 3))))
      if (p < 1) raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [inView, reduce, to])
  return (
    <div ref={ref} style={{ fontFamily: 'var(--serif)', fontSize: 'clamp(34px,4vw,52px)', lineHeight: 1 }}>
      {n.toLocaleString()}
    </div>
  )
}

export function StatStrip({ items }: { items: { num: number; label: string }[] }) {
  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: `repeat(${items.length},1fr)`,
        borderTop: '1px solid var(--line)',
        borderBottom: '1px solid var(--line)',
      }}
    >
      {items.map((it, i) => (
        <div
          key={it.label}
          style={{ padding: '26px 20px', borderRight: i < items.length - 1 ? '1px solid var(--line)' : 'none' }}
        >
          <CountUp to={it.num} />
          <div className="mono" style={{ marginTop: 9 }}>{it.label}</div>
        </div>
      ))}
    </div>
  )
}
