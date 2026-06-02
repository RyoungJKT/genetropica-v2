import { useSummary } from '../data/api'
import { StatStrip } from '../components/StatStrip'
import { useRegister, say } from '../state/register'

export default function Overview() {
  const { data, isLoading, error } = useSummary()
  const { reg } = useRegister()
  return (
    <div className="wrap" style={{ padding: '60px 0' }}>
      <div className="eyebrow">Drug repurposing for neglected tropical diseases</div>
      <h1 style={{ fontSize: 'clamp(40px,6.4vw,84px)', fontWeight: 360, letterSpacing: '-.035em', marginTop: 16 }}>
        100 approved drugs,<br />tested against the<br />diseases we forget.
      </h1>
      <p style={{ color: 'var(--ink-soft)', maxWidth: '40ch', lineHeight: 1.65, margin: '22px 0 32px' }}>
        {say(
          reg,
          'A computational screen of medicines that are already safe and approved, to see which could be repurposed against dengue, chikungunya and leptospirosis.',
          'A docking plus ML-prior repurposing screen of 100 approved drugs against 6 targets, ranked by Vina score and ligand efficiency over drug-like candidates.',
        )}
      </p>
      {isLoading && <p className="mono">Loading data...</p>}
      {error && <p className="mono" style={{ color: 'var(--clay)' }}>Failed to load data.</p>}
      {data && (
        <StatStrip
          items={[
            { num: data.drugs, label: 'Approved drugs screened' },
            { num: data.targets, label: 'Protein targets' },
            { num: data.diseases, label: 'Neglected diseases' },
            { num: data.docking_runs, label: 'Docking runs' },
          ]}
        />
      )}
    </div>
  )
}
