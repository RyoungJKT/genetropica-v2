import { Reveal } from './Reveal'
import { useT } from '../i18n'

const ITEMS = [
  { h: 'A prior, not a cure', p: 'These are computational predictions that point a scientist toward promising candidates. They are a starting hypothesis, never a treatment.' },
  { h: 'Sofosbuvir is a control', p: 'The known-active hepatitis C drug is included on purpose to check the method, not presented as a discovery.' },
  { h: 'Two metrics on purpose', p: 'Raw binding favours big molecules; efficiency favours tiny ones. Reporting both, over drug-like candidates, avoids fooling ourselves with size bias.' },
  { h: 'Caveats stay visible', p: 'Where validation was weak (the dengue NS5 docking AUC of 0.37, below random), it is stated plainly rather than hidden. The ML score is a target-agnostic prior, not a per-target oracle.' },
]

export function HonestyBand() {
  const { t } = useT()
  return (
    <section style={{ background: 'linear-gradient(160deg,#16261d,#1b3327 60%,#13231a)', color: 'var(--paper)' }}>
      <div className="wrap" style={{ padding: '90px 28px' }}>
        <Reveal>
          <div className="eyebrow" style={{ color: '#9ec7ad' }}>{t('What this is, and is not')}</div>
          <h2 style={{ color: 'var(--paper)', fontSize: 'clamp(28px,3.6vw,44px)', fontWeight: 380, maxWidth: '22ch', marginTop: 14 }}>{t("Strong on what it is. Clear on what it isn't.")}</h2>
        </Reveal>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2,1fr)', gap: 26, marginTop: 42 }}>
          {ITEMS.map((it, i) => (
            <Reveal key={it.h} delay={i * 0.06}>
              <div style={{ borderLeft: '2px solid var(--green-bright)', padding: '6px 0 6px 20px' }}>
                <h4 style={{ fontFamily: 'var(--serif)', fontSize: 19, color: '#f4f0e6', marginBottom: 7 }}>{t(it.h)}</h4>
                <p style={{ color: '#cfe0d4', fontSize: 14.5, lineHeight: 1.65, margin: 0 }}>{t(it.p)}</p>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  )
}
