import { useNs5Enrichment } from '../data/api'
import { useRegister, say } from '../state/register'
import { MultiLineChart, type ChartLine } from './MultiLineChart'

const GREEN = '#1F5740'

function Chip({ label, value }: { label: string; value: string }) {
  return (
    <span style={{ display: 'inline-flex', flexDirection: 'column', gap: 2, border: '1px solid var(--line)', borderRadius: 10, padding: '7px 12px', background: 'var(--paper)' }}>
      <span style={{ fontFamily: 'var(--mono)', fontSize: 9, letterSpacing: '.06em', textTransform: 'uppercase', color: 'var(--ink-faint)' }}>{label}</span>
      <span style={{ fontFamily: 'var(--mono)', fontSize: 15, color: 'var(--ink)' }}>{value}</span>
    </span>
  )
}

export function Ns5EnrichmentBenchmark() {
  const { reg } = useRegister()
  const q = useNs5Enrichment()
  const d = q.data
  if (!d) return null

  const rocLines: ChartLine[] = [
    { label: `Docking (Vina), AUC ${d.auc}`, color: GREEN, pts: d.roc },
    { label: 'Random', color: '#c9bfa8', pts: [[0, 0], [1, 1]] as [number, number][] },
  ]

  // Honest stats derived straight from the raw per-ligand scores (more negative = stronger).
  const entries = Object.entries(d.scores)
  const decoys = entries.filter(([k]) => k.startsWith('decoy_'))
  const sof = d.scores['sofosbuvir']
  const nDecoysBeatSof = decoys.filter(([, s]) => s < sof).length
  const strongest = entries.reduce((a, b) => (b[1] < a[1] ? b : a))
  const strongestIsDecoy = strongest[0].startsWith('decoy_')

  return (
    <div style={{ marginTop: 40, borderTop: '1px solid var(--line)', paddingTop: 30 }}>
      <div className="eyebrow" style={{ color: GREEN }}>Most rigorous test</div>
      <h3 style={{ fontSize: 26, fontWeight: 400, marginTop: 8 }}>Property-matched decoy benchmark (DUD-E-style)</h3>
      <p style={{ color: 'var(--ink-soft)', maxWidth: 780, lineHeight: 1.65, margin: '12px 0 0', fontSize: 15 }}>
        {say(reg,
          `The strict version of the test, the kind drug-screening papers use. Each of the ${d.n_actives} real inhibitors is matched to random look-alikes of similar size and chemistry but a different scaffold, then docking has to pick the real ones back out. It scored AUC ${d.auc}, below the 0.5 you would get by guessing, confirming the fair library result rather than the inflated easy-decoy one.`,
          `Retrospective enrichment against property-matched, topologically dissimilar (DUD-E-style) decoys, the standard rigorous decoy construction. ROC-AUC ${d.auc} (< 0.5) with zero early enrichment, independently confirming the fair library-based AUC rather than the inflated small-decoy test.`)}
      </p>

      <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', margin: '18px 0 6px' }}>
        <Chip label="ROC-AUC" value={`${d.auc} (< 0.5)`} />
        <Chip label="EF top 1%" value={`${d.ef['1pct']}x`} />
        <Chip label="Actives" value={String(d.n_actives)} />
        <Chip label="Decoys" value={String(d.n_decoys)} />
        <Chip label="Exhaustiveness" value={String(d.exhaustiveness)} />
      </div>

      <div style={{ marginTop: 18 }}>
        <MultiLineChart lines={rocLines} xLabel="false positive rate" yLabel="true positive rate" yMin={0} />
      </div>

      <p style={{ color: 'var(--ink-soft)', maxWidth: 780, lineHeight: 1.65, margin: '18px 0 0', fontSize: 14.5 }}>
        Docking ranks the genuine inhibitors <b>below</b> random look-alikes. {nDecoysBeatSof} of the {d.n_decoys} decoys out-score sofosbuvir, the approved positive control{strongestIsDecoy ? ', and the single strongest pose in the whole set is a decoy, not a real drug' : ''}. This is the expected failure mode here: the actives are nucleoside-analogue prodrugs, so the true binder is the triphosphate metabolite rather than the parent molecule that was docked, and NS5's metal-dependent active site is not captured by the rigid clean receptor. We report it plainly, for NS5, mechanism and published literature should outweigh the docking score.
      </p>
      <p style={{ color: 'var(--ink-faint)', maxWidth: 780, lineHeight: 1.6, margin: '10px 0 0', fontSize: 12.5 }}>
        NS5-only: it is the single target with protein-specific known actives. The other five have only whole-virus phenotypic data, which cannot anchor a docking enrichment test. Receptor {d.receptor}, same grid box as the original screen, AutoDock Vina on CPU.
      </p>
    </div>
  )
}
