import { useRegister } from '../state/register'
import { AXIS, BUCKETS } from '../lib/buckets'
import { Card } from './Card'

export function FieldPanel() {
  const { reg } = useRegister()
  const a = AXIS[reg]
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
      <Card>
        <h4 style={{ fontSize: 20, marginBottom: 8 }}>Read it like this</h4>
        <p style={{ fontSize: 13.5, color: 'var(--ink-soft)', lineHeight: 1.6, margin: 0 }}>{a.body}</p>
        <div style={{ fontFamily: 'var(--mono)', fontSize: 10.5, letterSpacing: '.06em', textTransform: 'uppercase', color: 'var(--ink-faint)', marginTop: 12 }}>
          X: {a.x} &rarr; &nbsp; Y: {a.y} &uarr; &nbsp; depth: size
        </div>
      </Card>
      <Card>
        <h4 style={{ fontSize: 20, marginBottom: 10 }}>Drug class</h4>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {Object.values(BUCKETS).map((b) => (
            <div key={b.key} style={{ display: 'flex', alignItems: 'center', gap: 10, fontSize: 13, color: 'var(--ink-soft)' }}>
              <span style={{ width: 13, height: 13, borderRadius: '50%', background: b.color, flex: 'none', boxShadow: '0 0 0 3px rgba(0,0,0,.04)' }} />
              {b.label}
            </div>
          ))}
        </div>
        <p style={{ fontSize: 12, color: 'var(--ink-faint)', fontStyle: 'italic', lineHeight: 1.5, marginTop: 14 }}>
          Faded spheres did not pass the safety (ADMET) filter. A green ring marks a drug-like candidate.
        </p>
      </Card>
    </div>
  )
}
