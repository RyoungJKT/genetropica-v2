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
          {t('Compounds are ranked by predicted AutoDock Vina binding affinity for the selected target; bar length reflects score magnitude. Switch to "By efficiency" to rank by ligand efficiency (affinity per heavy atom). Note the "outside drug-like range" tag: top raw scores often reflect larger molecular weight.')}
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
          {t('The drug-like badge marks candidates in the 250 to 600 Da range.')}
        </p>
      </Card>
    </div>
  )
}
