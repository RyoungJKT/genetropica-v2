import { BUCKETS } from '../lib/buckets'
import { Card } from './Card'
import { useT } from '../i18n'

export function FieldPanel() {
  const { t } = useT()
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
      <Card>
        <h4 style={{ fontSize: 20, marginBottom: 8 }}>{t('Read it like this')}</h4>
        <p style={{ fontSize: 13.5, color: 'var(--ink-soft)', lineHeight: 1.6, margin: 0 }}>
          {t('Every drug is ranked by how strongly it grips the chosen target; the bar is binding strength. Flip to "by efficiency" to rank by grip per atom instead. Watch the "outside drug-like range" tag: the very strongest binders are often just the biggest molecules.')}
        </p>
      </Card>
      <Card>
        <h4 style={{ fontSize: 20, marginBottom: 10 }}>{t('Drug class')}</h4>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {Object.values(BUCKETS).map((b) => (
            <div key={b.key} style={{ display: 'flex', alignItems: 'center', gap: 10, fontSize: 13, color: 'var(--ink-soft)' }}>
              <span style={{ width: 13, height: 13, borderRadius: '50%', background: b.color, flex: 'none' }} />
              {t(b.label)}
            </div>
          ))}
        </div>
        <p style={{ fontSize: 12, color: 'var(--ink-faint)', fontStyle: 'italic', lineHeight: 1.5, marginTop: 14 }}>
          {t('Faded rows did not pass the safety (ADMET) filter. The drug-like badge marks candidates in the 250 to 600 Da range.')}
        </p>
      </Card>
    </div>
  )
}
