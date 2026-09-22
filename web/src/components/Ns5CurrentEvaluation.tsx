import { useNs5EnrichmentCurrent } from '../data/api'
import { MultiLineChart, type ChartLine } from './MultiLineChart'
import { useT } from '../i18n'

const GREEN = '#1F5740'

function Chip({ label, value }: { label: string; value: string }) {
  return (
    <span style={{ display: 'inline-flex', flexDirection: 'column', gap: 2, border: '1px solid var(--line)', borderRadius: 10, padding: '7px 12px', background: 'var(--paper)' }}>
      <span style={{ fontFamily: 'var(--mono)', fontSize: 9, letterSpacing: '.06em', textTransform: 'uppercase', color: 'var(--ink-faint)' }}>{label}</span>
      <span style={{ fontFamily: 'var(--mono)', fontSize: 15, color: 'var(--ink)' }}>{value}</span>
    </span>
  )
}

const f2 = (x: number) => x.toFixed(2)

// The corrected NS5 benchmark: the current evaluation, shown first on the Validation page.
export function Ns5CurrentEvaluation() {
  const { t } = useT()
  const q = useNs5EnrichmentCurrent()
  const d = q.data
  if (!d) return null
  const lines: ChartLine[] = [
    { label: `${t('Docking (Vina), AUC')} ${f2(d.auc)}`, color: GREEN, pts: d.roc },
    { label: t('Random'), color: '#c9bfa8', pts: [[0, 0], [1, 1]] as [number, number][] },
  ]
  return (
    <div style={{ marginTop: 40, borderTop: '1px solid var(--line)', paddingTop: 30 }}>
      <div className="eyebrow" style={{ color: GREEN }}>{t('Current evaluation')}</div>
      <h3 style={{ fontSize: 26, fontWeight: 400, marginTop: 8 }}>{t('Property-matched decoy benchmark, corrected')}</h3>
      <p style={{ color: 'var(--ink-soft)', maxWidth: 780, lineHeight: 1.65, margin: '12px 0 0', fontSize: 15 }}>
        {/* split around the interpolations: t() keys on the literal string */}
        {t('Each of the')} {d.n_actives}{' '}
        {t('known NS5 inhibitors is matched to')} {d.decoys_per_active}{' '}
        {t('decoys of similar size, charge and chemistry, and all are docked into the catalytic site of 4V0R chain A with its magnesium ion kept. Docking scored AUC')}{' '}
        {f2(d.auc)} {t('(95% CI')} {f2(d.ci95[0])} {t('to')} {f2(d.ci95[1])}
        {t('), so it did not separate the inhibitors from the decoys.')}
      </p>
      <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', margin: '18px 0 6px' }}>
        <Chip label={t('ROC-AUC')} value={f2(d.auc)} />
        <Chip label={t('95% CI')} value={`${f2(d.ci95[0])} to ${f2(d.ci95[1])}`} />
        <Chip label={t('EF top 10%')} value={`${d.ef['10%']}x`} />
        <Chip label={t('Actives')} value={String(d.n_actives)} />
        <Chip label={t('Decoys')} value={String(d.n_decoys)} />
      </div>
      <div style={{ marginTop: 18 }}>
        <MultiLineChart lines={lines} xLabel={t('false positive rate')} yLabel={t('true positive rate')} yMin={0} />
      </div>
    </div>
  )
}
