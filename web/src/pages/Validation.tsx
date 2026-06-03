import { useValidation } from '../data/api'
import { useRegister, say } from '../state/register'
import { MultiLineChart, type ChartLine } from '../components/MultiLineChart'

const LABEL: Record<string, string> = { docking: 'Docking (Vina)', gnn: 'ML (RandomForest)', consensus: 'Consensus' }
const COLOR: Record<string, string> = { docking: '#1F5740', gnn: '#A8492B', consensus: '#A8742C' }

export default function Validation() {
  const v = useValidation()
  const { reg } = useRegister()
  const data = v.data
  const rocLines: ChartLine[] = data
    ? [
        ...(['docking', 'gnn', 'consensus'] as const)
          .filter((k) => data.roc[k]?.length)
          .map((k) => ({ label: LABEL[k], color: COLOR[k], pts: data.roc[k] })),
        { label: 'Random', color: '#c9bfa8', pts: [[0, 0], [1, 1]] as [number, number][] },
      ]
    : []

  return (
    <div className="wrap" style={{ padding: '56px 0' }}>
      <div className="eyebrow">Tool 08</div>
      <h1 style={{ fontSize: 'clamp(34px,5vw,60px)', fontWeight: 380, marginTop: 12 }}>Methodology Validation</h1>
      <p style={{ color: 'var(--ink-soft)', maxWidth: 760, lineHeight: 1.65, margin: '14px 0 0' }}>
        {say(reg,
          'Does the method actually pick out known-good drugs? We checked it against dengue NS5, and the honest answer is mixed.',
          'Retrospective enrichment test on dengue NS5: can the scoring separate known actives from decoys? Reported with both the inflated initial result and the fair one.')}
      </p>

      {data && rocLines.length > 0 && (
        <div style={{ marginTop: 30 }}>
          <h3 style={{ fontSize: 22 }}>ROC curve, initial small-decoy test (inflated)</h3>
          <p style={{ fontSize: 13.5, color: 'var(--ink-soft)', margin: '4px 0 12px', maxWidth: 760 }}>
            Against {String(data.metadata.n_actives ?? 8)} actives and {String(data.metadata.n_decoys ?? 78)} decoys. Curves hugging the top-left look excellent, but with so few easy decoys this overstates real performance. The diagonal is random.
          </p>
          <MultiLineChart lines={rocLines} xLabel="false positive rate" yLabel="true positive rate" yMin={0} />
        </div>
      )}

      {data && (
        <div style={{ marginTop: 30 }}>
          <h3 style={{ fontSize: 22 }}>Enrichment factors (same initial test)</h3>
          <p style={{ fontSize: 13.5, color: 'var(--ink-soft)', margin: '4px 0 12px', maxWidth: 760 }}>
            How many more actives appear in the top X% than by chance. Also from the inflated test, so read alongside the fair AUC of {data.fair_auc} for NS5 from the library-based test.
          </p>
          <div style={{ border: '1px solid var(--line)', borderRadius: 14, overflow: 'hidden', maxWidth: 520, background: 'var(--paper)' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13.5 }}>
              <thead><tr>{['Method', 'Top 1%', 'Top 5%', 'Top 10%'].map((h, i) => (
                <th key={h} style={{ textAlign: i === 0 ? 'left' : 'right', padding: '9px 14px', fontFamily: 'var(--mono)', fontSize: 10, letterSpacing: '.06em', textTransform: 'uppercase', color: 'var(--ink-faint)', borderBottom: '1px solid var(--line)' }}>{h}</th>
              ))}</tr></thead>
              <tbody>
                {Object.entries(data.ef).map(([k, e]) => (
                  <tr key={k} style={{ borderBottom: '1px solid var(--line)' }}>
                    <td style={{ padding: '9px 14px' }}>{LABEL[k] ?? k}</td>
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

      {!data && <p className="mono" style={{ marginTop: 20 }}>Loading validation data...</p>}
    </div>
  )
}
