import { useState } from 'react'
import { useSummary, useTargets, useField } from '../data/api'
import { useRegister, say } from '../state/register'
import { StatStrip } from '../components/StatStrip'
import { Reveal } from '../components/Reveal'
import { Steps } from '../components/Steps'
import { TargetCards } from '../components/TargetCards'
import { HonestyBand } from '../components/HonestyBand'
import { Footer } from '../components/Footer'
import { FieldPanel } from '../components/FieldPanel'
import { HeroMolecule } from '../three/HeroMolecule'
import { CandidateScatter } from '../charts/CandidateScatter'

const TARGET_ORDER = ['DENV_NS5', 'DENV_NS3', 'DENV_E', 'CHIKV_nsP2', 'CHIKV_nsP1', 'LEPTO_LipL32']

export default function Overview() {
  const { reg } = useRegister()
  const summary = useSummary()
  const targets = useTargets()
  const field = useField()
  const [sel, setSel] = useState('DENV_NS5')

  const targetName = (id: string) => targets.data?.find((t) => t.target_id === id)?.name ?? id
  const points = field.data?.[sel] ?? []
  const order = field.data ? TARGET_ORDER.filter((t) => field.data![t]) : []

  return (
    <>
      {/* hero */}
      <div className="wrap" style={{ display: 'grid', gridTemplateColumns: '1.05fr .95fr', alignItems: 'center', gap: 20, minHeight: '78vh', padding: '40px 0 30px' }}>
        <div>
          <div className="eyebrow">Drug repurposing for neglected tropical diseases</div>
          <h1 style={{ fontSize: 'clamp(40px,6.4vw,84px)', fontWeight: 360, letterSpacing: '-.035em', marginTop: 18, lineHeight: 1.0 }}>
            100 approved drugs,<br />tested against the<br />diseases we <em style={{ fontStyle: 'italic', color: 'var(--green)' }}>forget</em>.
          </h1>
          <p style={{ fontSize: 'clamp(16px,1.5vw,19px)', color: 'var(--ink-soft)', maxWidth: '34ch', lineHeight: 1.65, margin: '22px 0 28px' }}>
            {say(reg,
              'Dengue, chikungunya and leptospirosis affect millions, yet attract little new drug funding. GeneTropica screens medicines that are already safe and approved to see which could be repurposed.',
              'A docking plus ML-prior repurposing screen of 100 approved drugs against 6 targets, ranked by Vina score and ligand efficiency over drug-like candidates.')}
          </p>
          <a href="#field" style={{ fontFamily: 'var(--mono)', textTransform: 'uppercase', letterSpacing: '.12em', fontSize: 12, borderRadius: 100, padding: '13px 22px', border: '1px solid var(--ink)', background: 'var(--ink)', color: 'var(--paper)' }}>
            Explore the candidates
          </a>
        </div>
        <div style={{ height: 460 }}><HeroMolecule /></div>
      </div>

      {/* stats */}
      <div className="wrap">
        {summary.data && (
          <StatStrip items={[
            { num: summary.data.drugs, label: 'Approved drugs screened' },
            { num: summary.data.targets, label: 'Protein targets' },
            { num: summary.data.diseases, label: 'Neglected diseases' },
            { num: summary.data.docking_runs, label: 'Docking runs' },
          ]} />
        )}
      </div>

      <Steps />

      {/* candidate field */}
      <section id="field" style={{ background: 'var(--paper-2)', borderTop: '1px solid var(--line)', borderBottom: '1px solid var(--line)', padding: '92px 0' }}>
        <div className="wrap">
          <Reveal>
            <div className="eyebrow">The candidate field, live data</div>
            <h2 style={{ fontSize: 'clamp(28px,3.6vw,46px)', marginTop: 14 }}>Every drug, plotted by how it binds</h2>
            <p style={{ color: 'var(--ink-soft)', fontSize: 17, lineHeight: 1.7, margin: '18px 0 0', maxWidth: 760 }}>
              Each dot is one real drug docked against a chosen protein target. Hover any dot for a plain-English read, and switch the target to replot the whole field.
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

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 320px', gap: 30, alignItems: 'start' }}>
            <Reveal>
              {field.isLoading ? (
                <div className="mono" style={{ padding: 40 }}>Loading candidates...</div>
              ) : (
                <CandidateScatter key={sel} points={points} />
              )}
            </Reveal>
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
