import { useState, type ReactNode } from 'react'
import { useRegister, say } from '../state/register'
import { useField, useLiterature, useTargets } from '../data/api'

const LIT_ORDER = ['DENV_NS5', 'DENV_NS3', 'DENV_E', 'CHIKV_nsP2', 'CHIKV_nsP1', 'LEPTO_LipL32']

function LiteratureEvidence() {
  const lit = useLiterature()
  const field = useField()
  const targets = useTargets()
  const [tid, setTid] = useState('DENV_NS5')
  const tName = (id: string) => targets.data?.find((t) => t.target_id === id)?.name ?? id
  if (!lit.data || !field.data) return null
  const order = LIT_ORDER.filter((t) => field.data![t])
  const refsHere = lit.data.filter((r) => r.target === tid)
  const countByDrug: Record<string, number> = {}
  for (const r of refsHere) countByDrug[r.drug] = (countByDrug[r.drug] ?? 0) + 1
  const ranked = Object.entries(countByDrug).sort((a, b) => b[1] - a[1]).slice(0, 12)
  const maxC = ranked.length ? ranked[0][1] : 1
  const withRefs = new Set(refsHere.map((r) => r.drug))
  const novel = [...(field.data[tid] ?? [])].filter((p) => p.dl === 1 && !withRefs.has(p.name)).sort((a, b) => a.vina - b.vina).slice(0, 6)
  return (
    <div style={{ marginTop: 30 }}>
      <h3 style={{ fontSize: 22 }}>Literature evidence</h3>
      <p style={{ fontSize: 15, color: 'var(--ink-soft)', lineHeight: 1.7, margin: '8px 0 14px', maxWidth: 760 }}>
        PubMed references per drug for a target, found by keyword mining (so weak hits dominate and count only as a hint, not proof). Drugs that score well here yet have no prior literature are the more interesting, genuinely novel, leads.
      </p>
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 18 }}>
        {order.map((id) => (
          <button key={id} onClick={() => setTid(id)} style={{ fontFamily: 'var(--mono)', fontSize: 11, letterSpacing: '.06em', textTransform: 'uppercase', padding: '8px 14px', borderRadius: 100, cursor: 'pointer', border: '1px solid var(--line)', background: tid === id ? 'var(--green)' : 'var(--paper)', color: tid === id ? 'var(--paper)' : 'var(--ink-soft)' }}>{tName(id)}</button>
        ))}
      </div>
      <div className="rstack" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 28 }}>
        <div>
          <h4 style={{ fontSize: 14, marginBottom: 10 }}>References per drug</h4>
          {ranked.length ? ranked.map(([drug, c]) => (
            <div key={drug} style={{ display: 'grid', gridTemplateColumns: '120px 1fr 24px', gap: 8, alignItems: 'center', margin: '6px 0' }}>
              <span style={{ fontSize: 12.5, color: 'var(--ink-soft)', textTransform: 'capitalize', textAlign: 'right', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{drug.replace(/_/g, ' ')}</span>
              <div style={{ background: 'var(--paper-3)', borderRadius: 4, height: 13, overflow: 'hidden' }}><div className="bar" style={{ width: `${(c / maxC) * 100}%`, height: '100%', background: 'var(--teal)', borderRadius: 4 }} /></div>
              <span style={{ fontFamily: 'var(--mono)', fontSize: 11 }}>{c}</span>
            </div>
          )) : <p style={{ fontSize: 13, color: 'var(--ink-faint)' }}>No references for this target.</p>}
        </div>
        <div>
          <h4 style={{ fontSize: 14, marginBottom: 10 }}>Novel-discovery candidates</h4>
          <p style={{ fontSize: 11.5, color: 'var(--ink-faint)', margin: '0 0 8px' }}>Drug-like, top binders here, with no prior literature.</p>
          {novel.length ? novel.map((p) => (
            <div key={p.name} style={{ display: 'flex', justifyContent: 'space-between', padding: '7px 0', borderBottom: '1px solid var(--line)', fontSize: 13 }}>
              <span style={{ textTransform: 'capitalize' }}>{p.name.replace(/_/g, ' ')}</span>
              <span style={{ fontFamily: 'var(--mono)', color: 'var(--ink-soft)' }}>{p.vina} kcal/mol</span>
            </div>
          )) : <p style={{ fontSize: 13, color: 'var(--ink-faint)' }}>None.</p>}
        </div>
      </div>
    </div>
  )
}

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

      <LiteratureEvidence />
    </div>
  )
}
