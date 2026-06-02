import { useTargets } from '../data/api'
import type { Target } from '../data/types'
import { Reveal } from './Reveal'

const ROLES: Record<string, string> = {
  DENV_NS5: 'The copy machine the virus uses to multiply. Jam it and the virus cannot replicate.',
  DENV_NS3: 'Molecular scissors and an unzipper the virus needs to mature its proteins.',
  DENV_E: 'The key the virus turns to enter a human cell in the first place.',
  CHIKV_nsP2: 'The enzyme that cuts the virus freshly made proteins into working parts.',
  CHIKV_nsP1: 'Protects the virus genetic messages so the cell will read them.',
  LEPTO_LipL32: 'An abundant surface protein of the Leptospira bacterium, and a drug target.',
}

function validated(vs: string) {
  return /auc|0\.37|retrospective validation performed/i.test(vs || '')
}

export function TargetCards() {
  const { data } = useTargets()
  if (!data) return null
  const byDisease = new Map<string, Target[]>()
  for (const t of data) {
    if (!byDisease.has(t.disease)) byDisease.set(t.disease, [])
    byDisease.get(t.disease)!.push(t)
  }
  return (
    <section style={{ padding: '92px 0' }}>
      <div className="wrap">
        <Reveal>
          <div className="eyebrow">Six doors into three diseases</div>
          <h2 style={{ fontSize: 'clamp(28px,3.6vw,46px)', marginTop: 14 }}>The proteins we aim at</h2>
          <p style={{ color: 'var(--ink-soft)', fontSize: 17, lineHeight: 1.7, margin: '18px 0 0', maxWidth: 720 }}>
            A pathogen depends on a handful of proteins to enter cells, copy itself and mature. Block one and you can stop the disease.
          </p>
        </Reveal>
        {[...byDisease.entries()].map(([disease, targets]) => (
          <div key={disease} style={{ marginTop: 34 }}>
            <h3 style={{ fontSize: 26, marginBottom: 16, textTransform: 'capitalize' }}>{disease}</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 20 }}>
              {targets.map((t) => (
                <Reveal key={t.target_id}>
                  <div style={{ border: '1px solid var(--line)', borderRadius: 16, padding: 22, background: 'var(--paper)', height: '100%' }}>
                    <div style={{ fontFamily: 'var(--mono)', fontSize: 10, letterSpacing: '.1em', color: 'var(--clay)', textTransform: 'uppercase' }}>PDB {t.pdb_id}</div>
                    <h4 style={{ fontSize: 21, margin: '8px 0 10px' }}>{t.name}</h4>
                    <p style={{ fontSize: 14, color: 'var(--ink-soft)', lineHeight: 1.6, margin: 0 }}>{ROLES[t.target_id] ?? ''}</p>
                    <span style={{ display: 'inline-block', marginTop: 12, fontFamily: 'var(--mono)', fontSize: 9.5, letterSpacing: '.06em', textTransform: 'uppercase', borderRadius: 100, padding: '3px 9px', border: '1px solid var(--line)', color: validated(t.validation_status) ? 'var(--clay)' : 'var(--ink-faint)' }}>
                      {validated(t.validation_status) ? 'Validated: AUC 0.37 (below random)' : 'Not yet validated, hypothesis only'}
                    </span>
                  </div>
                </Reveal>
              ))}
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}
