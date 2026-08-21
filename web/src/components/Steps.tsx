import { Reveal } from './Reveal'
import { useT } from '../i18n'

const STEPS = [
  { n: '1', h: 'Start with safe drugs', p: 'Begin with 100 medicines already approved by regulators, so their safety in humans is established. No need to start from scratch.', chip: 'FDA-approved library' },
  { n: '2', h: 'Simulate the grip', p: 'For each drug, simulate how tightly it latches onto a protein the pathogen needs to survive. A tighter, well-fitted grip means more potential to disrupt the disease.', chip: 'AutoDock Vina, 50 ns MD' },
  { n: '3', h: 'Rank the realistic ones', p: 'Score every candidate two ways to avoid bias, keep the drug-like and safe ones, and surface the most promising classes for a scientist to follow up.', chip: 'Dual-metric ranking' },
]

export function Steps() {
  const { t } = useT()
  return (
    <section style={{ padding: '92px 0' }}>
      <div className="wrap">
        <Reveal>
          <div className="eyebrow">{t('The idea in three steps')}</div>
          <h2 style={{ fontSize: 'clamp(28px,3.6vw,46px)', marginTop: 14 }}>{t('Reusing medicine we already trust')}</h2>
          <p style={{ color: 'var(--ink-soft)', fontSize: 17, lineHeight: 1.7, margin: '18px 0 0', maxWidth: 720 }}>
            {t('Inventing a new drug takes a decade and a billion dollars. Repurposing asks a faster question: could a medicine that is already approved and known to be safe also work against a neglected disease?')}
          </p>
        </Reveal>
        <div className="rstack" style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 24, marginTop: 46 }}>
          {STEPS.map((s, i) => (
            <Reveal key={s.n} delay={i * 0.08}>
              <div style={{ position: 'relative', padding: '30px 26px', border: '1px solid var(--line)', borderRadius: 16, background: 'linear-gradient(180deg,var(--paper-2),var(--paper))', overflow: 'hidden', height: '100%' }}>
                <div style={{ fontFamily: 'var(--serif)', fontSize: 64, color: 'var(--paper-3)', position: 'absolute', top: 6, right: 18, lineHeight: 1 }}>{s.n}</div>
                <h3 style={{ fontSize: 23, marginBottom: 10, position: 'relative' }}>{t(s.h)}</h3>
                <p style={{ color: 'var(--ink-soft)', lineHeight: 1.65, fontSize: 15, position: 'relative' }}>{t(s.p)}</p>
                <span style={{ display: 'inline-block', fontFamily: 'var(--mono)', fontSize: 10, letterSpacing: '.08em', textTransform: 'uppercase', color: 'var(--green)', border: '1px solid var(--line)', borderRadius: 100, padding: '4px 10px', marginTop: 16, background: 'var(--paper)' }}>{t(s.chip)}</span>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  )
}
