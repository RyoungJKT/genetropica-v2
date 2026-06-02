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

      <div style={{ marginTop: 22, background: 'linear-gradient(160deg,#2a1a14,#3a241b 60%,#241410)', color: 'var(--paper)', borderRadius: 14, padding: '22px 24px', maxWidth: 820 }}>
        <div className="eyebrow" style={{ color: '#e0a98f' }}>The honest headline</div>
        <p style={{ fontSize: 15.5, lineHeight: 1.65, marginTop: 10, color: '#f0e6df' }}>
          An initial test against 8 known inhibitors and only 78 weakly-matched decoys gave a near-perfect score (docking AUC {data?.auc.docking ?? '0.95'}, ML AUC {data?.auc.gnn ?? '1.00'}). That is <b>too good to trust</b>: too few, too-easy decoys. On a fairer, library-based test, Vina scored <b>AUC {data?.fair_auc ?? 0.37} for NS5, below random</b>. The real inhibitors are small nucleoside analogues that dock weakly versus large molecules. We show the inflated curve below for transparency, not as a result.
        </p>
      </div>

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
            How many more actives appear in the top X% than by chance. Also from the inflated test, so read alongside the fair AUC {data.fair_auc} above.
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
