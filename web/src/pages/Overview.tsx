import { useState } from 'react'
import { useSummary, useTargets, useField } from '../data/api'
import { StatStrip } from '../components/StatStrip'
import { Reveal } from '../components/Reveal'
import { Steps } from '../components/Steps'
import { TargetCards } from '../components/TargetCards'
import { HonestyBand } from '../components/HonestyBand'
import { Footer } from '../components/Footer'
import { FieldPanel } from '../components/FieldPanel'
import { HeroMolecule } from '../three/HeroMolecule'
import { CandidateBoard } from '../charts/CandidateBoard'
import { useIsMobile } from '../lib/useIsMobile'
import { useT } from '../i18n'

const TARGET_ORDER = ['DENV_NS5', 'DENV_NS3', 'DENV_E', 'CHIKV_nsP2', 'CHIKV_nsP1', 'LEPTO_LipL32']

export default function Overview() {
  const { t } = useT()
  const summary = useSummary()
  const targets = useTargets()
  const field = useField()
  const [sel, setSel] = useState('DENV_NS5')
  const isMobile = useIsMobile()

  const targetName = (id: string) => targets.data?.find((t) => t.target_id === id)?.name ?? id
  const points = field.data?.[sel] ?? []
  const order = field.data ? TARGET_ORDER.filter((t) => field.data![t]) : []

  return (
    <>
      {/* hero */}
      <div className="wrap" style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : '1.05fr .95fr', alignItems: 'center', gap: 20, minHeight: isMobile ? 'auto' : '78vh', padding: isMobile ? '26px 0 8px' : '40px 0 30px' }}>
        <div>
          <div className="eyebrow">{t('Drug repurposing for neglected tropical diseases')}</div>
          <h1 style={{ fontSize: 'clamp(36px,4.9vw,72px)', fontWeight: 380, letterSpacing: '-.03em', marginTop: 18, lineHeight: 1.05 }}>
            {t('100 approved drugs,')}<br />{t('tested against the')}<br />{t('diseases we')} <em style={{ fontStyle: 'italic', color: 'var(--green)' }}>{t('forget')}</em>.
          </h1>
          <p style={{ fontSize: 'clamp(16px,1.5vw,19px)', color: 'var(--ink-soft)', maxWidth: '34ch', lineHeight: 1.65, margin: '22px 0 28px' }}>
            {t('Dengue, chikungunya and leptospirosis affect millions, yet attract little new drug funding. GeneTropica screens medicines that are already safe and approved to see which could be repurposed.')}
          </p>
          <a href="#field" style={{ fontFamily: 'var(--mono)', textTransform: 'uppercase', letterSpacing: '.12em', fontSize: 12, borderRadius: 100, padding: '13px 22px', border: '1px solid var(--ink)', background: 'var(--ink)', color: 'var(--paper)' }}>
            {t('Explore the candidates')}
          </a>
        </div>
        <div style={{ height: isMobile ? 260 : 460 }}><HeroMolecule /></div>
      </div>

      {/* stats */}
      <div className="wrap">
        {summary.data && (
          <StatStrip items={[
            { num: summary.data.drugs, label: t('Approved drugs screened') },
            { num: summary.data.targets, label: t('Protein targets') },
            { num: summary.data.diseases, label: t('Neglected diseases') },
            { num: summary.data.docking_runs, label: t('Docking runs') },
          ]} />
        )}
      </div>

      <Steps />

      {/* candidate field */}
      <section id="field" style={{ background: 'var(--paper-2)', borderTop: '1px solid var(--line)', borderBottom: '1px solid var(--line)', padding: '92px 0' }}>
        <div className="wrap">
          <Reveal>
            <div className="eyebrow">{t('The candidate field, live data')}</div>
            <h2 style={{ fontSize: 'clamp(28px,3.6vw,46px)', marginTop: 14 }}>{t('Every drug, ranked by how it binds')}</h2>
            <p style={{ color: 'var(--ink-soft)', fontSize: 17, lineHeight: 1.7, margin: '18px 0 0', maxWidth: 760 }}>
              {t('Every drug ranked by how strongly it binds the chosen target. Switch the target to re-rank, sort by efficiency, or hover a row for a plain-English read.')}
            </p>
          </Reveal>

          {/* target switcher */}
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', margin: '24px 0 22px' }}>
            {order.map((id) => (
              <button key={id} onClick={() => setSel(id)}
                style={{
                  fontFamily: 'var(--mono)', fontSize: 11, letterSpacing: '.06em', textTransform: 'uppercase',
                  padding: '8px 14px', borderRadius: 100, cursor: 'pointer',
                  border: '1px solid var(--line)',
                  background: sel === id ? 'var(--green)' : 'var(--paper)',
                  color: sel === id ? 'var(--paper)' : 'var(--ink-soft)',
                }}>
                {targetName(id)}
              </button>
            ))}
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : '1fr 320px', gap: 30, alignItems: 'start' }}>
            {field.isLoading ? (
              <div className="mono" style={{ padding: 40 }}>{t('Loading candidates...')}</div>
            ) : (
              <CandidateBoard key={sel} points={points} />
            )}
            <FieldPanel />
          </div>
        </div>
      </section>

      <TargetCards />
      <HonestyBand />
      <Footer />
    </>
  )
}
