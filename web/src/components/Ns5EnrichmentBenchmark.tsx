import { useNs5Enrichment } from '../data/api'
import { MultiLineChart, type ChartLine } from './MultiLineChart'
import { useT } from '../i18n'

// Grey, not the site green: this run is superseded by Ns5CurrentEvaluation.
const GREY = '#8a8a85'

function Chip({ label, value }: { label: string; value: string }) {
  return (
    <span style={{ display: 'inline-flex', flexDirection: 'column', gap: 2, border: '1px solid var(--line)', borderRadius: 10, padding: '7px 12px', background: 'var(--paper)' }}>
      <span style={{ fontFamily: 'var(--mono)', fontSize: 9, letterSpacing: '.06em', textTransform: 'uppercase', color: 'var(--ink-faint)' }}>{label}</span>
      <span style={{ fontFamily: 'var(--mono)', fontSize: 15, color: 'var(--ink)' }}>{value}</span>
    </span>
  )
}

export function Ns5EnrichmentBenchmark() {
  const { t } = useT()
  const q = useNs5Enrichment()
  const d = q.data
  if (!d) return null

  const rocLines: ChartLine[] = [
    { label: `${t('Docking (Vina), AUC')} ${d.auc}`, color: GREY, pts: d.roc },
    { label: t('Random'), color: '#c9bfa8', pts: [[0, 0], [1, 1]] as [number, number][] },
  ]

  return (
    <div style={{ marginTop: 40, borderTop: '1px solid var(--line)', paddingTop: 30 }}>
      <div className="eyebrow" style={{ color: 'var(--ink-faint)' }}>{t('Superseded benchmark')}</div>
      <h3 style={{ fontSize: 26, fontWeight: 400, marginTop: 8 }}>{t('Property-matched decoy benchmark (DUD-E-style)')}</h3>
      <p style={{ color: 'var(--ink-soft)', maxWidth: 780, lineHeight: 1.65, margin: '12px 0 0', fontSize: 15 }}>
        {t('The search box for this run sat off the catalytic site, and two of the eight inhibitors had no matched decoys. Kept for reference.')}
      </p>

      <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', margin: '18px 0 6px' }}>
        <Chip label={t('ROC-AUC')} value={String(d.auc)} />
        <Chip label={t('EF top 1%')} value={`${d.ef['1pct']}x`} />
        <Chip label={t('Actives')} value={String(d.n_actives)} />
        <Chip label={t('Decoys')} value={String(d.n_decoys)} />
        <Chip label={t('Exhaustiveness')} value={String(d.exhaustiveness)} />
      </div>

      <div style={{ marginTop: 18 }}>
        <MultiLineChart lines={rocLines} xLabel={t('false positive rate')} yLabel={t('true positive rate')} yMin={0} />
      </div>

      <p style={{ color: 'var(--ink-faint)', maxWidth: 780, lineHeight: 1.6, margin: '10px 0 0', fontSize: 12.5 }}>
        {t('NS5-only: it is the single target with protein-specific known actives. The other five have only whole-virus phenotypic data, which cannot anchor a docking enrichment test. Receptor')} {d.receptor}{t(', same grid box as the original screen, AutoDock Vina on CPU.')}
      </p>
    </div>
  )
}
