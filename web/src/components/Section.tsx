import type { ReactNode } from 'react'
import { Reveal } from './Reveal'

export function Section({ eyebrow, title, children }: { eyebrow?: string; title: string; children?: ReactNode }) {
  return (
    <section style={{ padding: '92px 0' }}>
      <div className="wrap">
        <Reveal>
          {eyebrow && <div className="eyebrow">{eyebrow}</div>}
          <h2 style={{ fontSize: 'clamp(28px,3.6vw,46px)', marginTop: 14 }}>{title}</h2>
        </Reveal>
        <div style={{ marginTop: 24, color: 'var(--ink-soft)', lineHeight: 1.7 }}>{children}</div>
      </div>
    </section>
  )
}
