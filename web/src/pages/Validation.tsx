import { useValidation } from '../data/api'
import { MultiLineChart, type ChartLine } from '../components/MultiLineChart'
import { Ns5EnrichmentBenchmark } from '../components/Ns5EnrichmentBenchmark'
import { Ns5CurrentEvaluation } from '../components/Ns5CurrentEvaluation'
import { useT } from '../i18n'

const LABEL: Record<string, string> = { docking: 'Docking (Vina)', gnn: 'ML (RandomForest)', consensus: 'Consensus' }
const COLOR: Record<string, string> = { docking: '#1F5740', gnn: '#A8492B', consensus: '#A8742C' }

// Russell's reflection on auditing the NS5 benchmark, verbatim.
const REFLECTION = [
  'Auditing my initial results changed how I judge computational evidence. I identified problems in both the docking setup and the construction of the comparison set. These problems meant that the earlier scores could not support the biological conclusions I had attached to them.',
  'To address these findings, I added checks that stop the workflow when the intended binding site is not properly represented. I also required complete and balanced decoy assignments and reported uncertainty alongside the performance estimate. I also added an analysis comparing each active compound with its own matched decoys.',
  'The corrected run produced an AUC of 0.49, with a confidence interval spanning 0.50. It therefore did not demonstrate useful discrimination in this evaluation. I learned that correcting an experiment can make its conclusions more defensible even when the result remains inconclusive.',
  'This experience shifted my attention toward the assumptions behind each output: which molecular species I was testing, whether the receptor setup represented the intended question, and whether the benchmark supported the interpretation. My next priorities are expanding the evaluation set and checking that the machine-learning training data match the intended biological target.',
]

export default function Validation() {
  const { t } = useT()
  const v = useValidation()
  const data = v.data
  const rocLines: ChartLine[] = data
    ? [
        ...(['docking', 'gnn', 'consensus'] as const)
          .filter((k) => data.roc[k]?.length)
          .map((k) => ({ label: t(LABEL[k]), color: COLOR[k], pts: data.roc[k] })),
        { label: t('Random'), color: '#c9bfa8', pts: [[0, 0], [1, 1]] as [number, number][] },
      ]
    : []

  return (
    <div className="wrap" style={{ padding: '56px 0' }}>
      <div className="eyebrow">{t('Tool 08')}</div>
      <h1 style={{ fontSize: 'clamp(34px,5vw,60px)', fontWeight: 380, marginTop: 12 }}>{t('Methodology Validation')}</h1>
      <p style={{ color: 'var(--ink-soft)', maxWidth: 760, lineHeight: 1.65, margin: '14px 0 0' }}>
        {t('This page documents the evaluation of GeneTropica’s screening workflow, the methodological issues identified during an audit, and the subsequent corrections. The current evaluation appears first. Earlier evaluations are retained below with explanations of why they were withdrawn.')}
      </p>

      <section style={{ marginTop: 40, borderTop: '1px solid var(--line)', paddingTop: 30 }}>
        <h3 style={{ fontSize: 26, fontWeight: 400 }}>{t('What I learned from auditing the results')}</h3>
        <div className="eyebrow" style={{ marginTop: 8 }}>{t('Research reflection by Russell Young')}</div>
        {REFLECTION.map((para) => (
          <p key={para} style={{ color: 'var(--ink-soft)', maxWidth: 780, lineHeight: 1.65, margin: '14px 0 0', fontSize: 15 }}>
            {t(para)}
          </p>
        ))}
      </section>

      <Ns5CurrentEvaluation />

      <Ns5EnrichmentBenchmark />

      {data && rocLines.length > 0 && (
        <div style={{ marginTop: 30 }}>
          <div className="eyebrow" style={{ color: 'var(--ink-faint)' }}>{t('Superseded')}</div>
          <h3 style={{ fontSize: 22, marginTop: 6 }}>{t('ROC curve, initial small-decoy test (inflated)')}</h3>
          <p style={{ fontSize: 13.5, color: 'var(--ink-soft)', margin: '4px 0 12px', maxWidth: 760 }}>
            {t('Against')} {String(data.metadata.n_actives ?? 8)} {t('actives and')} {String(data.metadata.n_decoys ?? 78)} {t('decoys. Curves hugging the top-left look excellent, but with so few easy decoys this overstates real performance. The diagonal is random.')}
          </p>
          <MultiLineChart lines={rocLines} xLabel={t('false positive rate')} yLabel={t('true positive rate')} yMin={0} />
        </div>
      )}

      {data && (
        <div style={{ marginTop: 30 }}>
          <div className="eyebrow" style={{ color: 'var(--ink-faint)' }}>{t('Superseded')}</div>
          <h3 style={{ fontSize: 22, marginTop: 6 }}>{t('Enrichment factors (same initial test)')}</h3>
          <p style={{ fontSize: 13.5, color: 'var(--ink-soft)', margin: '4px 0 12px', maxWidth: 760 }}>
            {t('How many more actives appear in the top X% than by chance, from the same small-decoy test, so these values are inflated too.')}
          </p>
          <div style={{ border: '1px solid var(--line)', borderRadius: 14, overflow: 'hidden', maxWidth: 520, background: 'var(--paper)' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13.5 }}>
              <thead><tr>{['Method', 'Top 1%', 'Top 5%', 'Top 10%'].map((h, i) => (
                <th key={h} style={{ textAlign: i === 0 ? 'left' : 'right', padding: '9px 14px', fontFamily: 'var(--mono)', fontSize: 10, letterSpacing: '.06em', textTransform: 'uppercase', color: 'var(--ink-faint)', borderBottom: '1px solid var(--line)' }}>{t(h)}</th>
              ))}</tr></thead>
              <tbody>
                {Object.entries(data.ef).map(([k, e]) => (
                  <tr key={k} style={{ borderBottom: '1px solid var(--line)' }}>
                    <td style={{ padding: '9px 14px' }}>{t(LABEL[k] ?? k)}</td>
                    <td style={{ padding: '9px 14px', textAlign: 'right', fontFamily: 'var(--mono)' }}>{e.ef_1pct}x</td>
                    <td style={{ padding: '9px 14px', textAlign: 'right', fontFamily: 'var(--mono)' }}>{e.ef_5pct}x</td>
                    <td style={{ padding: '9px 14px', textAlign: 'right', fontFamily: 'var(--mono)' }}>{e.ef_10pct}x</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {!data && <p className="mono" style={{ marginTop: 20 }}>{t('Loading validation data...')}</p>}
    </div>
  )
}
