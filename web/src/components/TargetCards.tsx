import { useTargets } from '../data/api'
import type { Target } from '../data/types'
import { Reveal } from './Reveal'
import { useIsMobile } from '../lib/useIsMobile'
import { useT } from '../i18n'

const ROLES: Record<string, string> = {
  DENV_NS5: 'Catalyzes viral RNA synthesis; inhibiting its active site blocks genome replication.',
  DENV_NS3: 'Bifunctional protease–helicase required for viral polyprotein processing and RNA unwinding.',
  DENV_E: 'Mediates host-cell attachment and pH-dependent membrane fusion during viral entry.',
  CHIKV_nsP2: 'Cleaves the viral non-structural polyprotein into mature functional subunits.',
  CHIKV_nsP1: "Catalyzes 5'-RNA capping to stabilize viral transcripts and enable host translation.",
  LEPTO_LipL32: 'Major outer-membrane lipoprotein of pathogenic Leptospira spp., evaluated here as a candidate surface target.',
}

function validated(vs: string) {
  return /auc|retrospective (test|validation) performed/i.test(vs || '')
}

export function TargetCards() {
  const { t } = useT()
  const { data } = useTargets()
  const isMobile = useIsMobile()
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
          <div className="eyebrow">{t('Six doors into three diseases')}</div>
          <h2 style={{ fontSize: 'clamp(28px,3.6vw,46px)', marginTop: 14 }}>{t('The proteins we aim at')}</h2>
          <p style={{ color: 'var(--ink-soft)', fontSize: 17, lineHeight: 1.7, margin: '18px 0 0', maxWidth: 720 }}>
            {t('A pathogen depends on a handful of proteins to enter cells, copy itself and mature. Block one and you can stop the disease.')}
          </p>
        </Reveal>
        {[...byDisease.entries()].map(([disease, targets]) => (
          <div key={disease} style={{ marginTop: 34 }}>
            <h3 style={{ fontSize: 26, marginBottom: 16, textTransform: 'capitalize' }}>{disease}</h3>
            <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : 'repeat(3,1fr)', gap: 20 }}>
              {targets.map((target) => (
                <Reveal key={target.target_id}>
                  <div style={{ border: '1px solid var(--line)', borderRadius: 16, padding: 22, background: 'var(--paper)', height: '100%' }}>
                    <div style={{ fontFamily: 'var(--mono)', fontSize: 10, letterSpacing: '.1em', color: 'var(--clay)', textTransform: 'uppercase' }}>PDB {target.pdb_id}</div>
                    <h4 style={{ fontSize: 21, margin: '8px 0 10px' }}>{target.name}</h4>
                    <p style={{ fontSize: 14, color: 'var(--ink-soft)', lineHeight: 1.6, margin: 0 }}>{ROLES[target.target_id] ? t(ROLES[target.target_id]) : ''}</p>
                    {validated(target.validation_status) && (
                      <span style={{ display: 'inline-block', marginTop: 12, fontFamily: 'var(--mono)', fontSize: 9.5, letterSpacing: '.06em', textTransform: 'uppercase', borderRadius: 100, padding: '3px 9px', border: '1px solid var(--line)', color: 'var(--clay)' }}>
                        {t('Benchmark: ROC-AUC 0.49 (no enrichment over random)')}
                      </span>
                    )}
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
