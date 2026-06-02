import type { ReactNode } from 'react'
import { useRegister, say } from '../state/register'

function Block({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div style={{ marginTop: 30 }}>
      <h3 style={{ fontSize: 22 }}>{title}</h3>
      <p style={{ fontSize: 15, color: 'var(--ink-soft)', lineHeight: 1.7, margin: '8px 0 0', maxWidth: 760 }}>{children}</p>
    </div>
  )
}

export default function Insights() {
  const { reg } = useRegister()
  return (
    <div className="wrap" style={{ padding: '56px 0' }}>
      <div className="eyebrow">Tool 06</div>
      <h1 style={{ fontSize: 'clamp(34px,5vw,60px)', fontWeight: 380, marginTop: 12 }}>AI Insights</h1>
      <p style={{ color: 'var(--ink-soft)', maxWidth: 760, lineHeight: 1.65, margin: '14px 0 0' }}>
        {say(reg,
          'Alongside the docking, a machine-learning model gives each drug a score. It is best understood as a sanity nudge, a prior, not a verdict on any one target.',
          'A machine-learning activity prior complements the physics-based docking. It is a target-agnostic ligand prior, not a per-target affinity predictor.')}
      </p>

      <Block title="What the model is">
        A scikit-learn RandomForest trained on 166 compounds from ChEMBL with measured RdRp activity, using a 2048-bit Morgan fingerprint plus the normalised Vina score as features. Its cross-validated AUC is 0.875. (An earlier version of the dashboard mislabelled this as a GNN; it is a RandomForest.)
      </Block>

      <Block title="What it is not">
        It is <b>target-agnostic</b>: the same drug receives the same ML score for every target, because the model never sees the specific binding pocket. So it is a prior, a broad activity hint, not a per-target prediction. Treat it as one weak signal among several, not a ranking on its own.
      </Block>

      <div style={{ marginTop: 30, background: 'linear-gradient(160deg,#16261d,#1b3327 60%,#13231a)', color: 'var(--paper)', borderRadius: 14, padding: '22px 24px', maxWidth: 820 }}>
        <div className="eyebrow" style={{ color: '#9ec7ad' }}>The honest result for NS5</div>
        <p style={{ fontSize: 15.5, lineHeight: 1.65, marginTop: 10, color: '#e9efe9' }}>
          On a fair retrospective test, docking scored <b>AUC 0.37 for dengue NS5, below random</b>. The genuine small-molecule inhibitors are nucleoside analogues that dock weakly compared with large molecules, a size-bias artefact. We report this openly: for NS5, mechanism and published literature should carry more weight than the docking or ML score. Only NS5 was retrospectively validated; the other five targets have no equivalent test.
        </p>
      </div>

      <Block title="Why two metrics, not one">
        Raw Vina score favours large molecules; ligand efficiency (grip per atom) favours small ones. Reporting both, over drug-like candidates only, keeps either bias from dominating, which is exactly why the candidate ranking shows both side by side.
      </Block>
    </div>
  )
}
