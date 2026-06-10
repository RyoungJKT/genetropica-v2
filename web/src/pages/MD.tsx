import type { ReactNode, CSSProperties } from 'react'
import { useState } from 'react'
import { MdAnimator } from '../components/md/MdAnimator'
import { useMd } from '../data/api'
import { useRegister, say } from '../state/register'
import { MultiLineChart, type ChartLine } from '../components/MultiLineChart'
import type { MdSeries, Md } from '../data/types'
import { useInView } from '../lib/anim'

const DRUGS = ['celecoxib', 'methotrexate', 'dasabuvir'] as const
const COLOR: Record<string, string> = { celecoxib: '#1F5740', methotrexate: '#A8492B', dasabuvir: '#A8742C' }
const LABEL: Record<string, string> = { celecoxib: 'Celecoxib', methotrexate: 'Methotrexate', dasabuvir: 'Dasabuvir' }
const tdR: CSSProperties = { padding: '9px 14px', textAlign: 'right', fontFamily: 'var(--mono)', fontSize: 12, color: 'var(--ink-soft)', whiteSpace: 'nowrap' }

function ChartBlock({ title, caption, children }: { title: string; caption: string; children: ReactNode }) {
  return (
    <div style={{ marginTop: 34 }}>
      <h3 style={{ fontSize: 22 }}>{title}</h3>
      <p style={{ fontSize: 13.5, color: 'var(--ink-soft)', lineHeight: 1.55, margin: '4px 0 12px', maxWidth: 760 }}>{caption}</p>
      {children}
    </div>
  )
}

function TopContacts({ md }: { md: Md }) {
  const [ref, inView] = useInView<HTMLDivElement>()
  return (
    <div ref={ref} style={{ marginTop: 34 }}>
      <h3 style={{ fontSize: 22 }}>Top contact residues</h3>
      <p style={{ fontSize: 13.5, color: 'var(--ink-soft)', lineHeight: 1.55, margin: '4px 0 14px', maxWidth: 760 }}>
        The protein residues each drug touches most over the run (percentage of frames in contact). Residues shared between drugs point to a common binding site.
      </p>
      <div className="rstack" style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 24 }}>
        {DRUGS.map((d) => {
          const contacts = md.series[d]?.contacts ?? []
          const max = contacts.length ? contacts[0][1] : 100
          return (
            <div key={d}>
              <div style={{ fontFamily: 'var(--mono)', fontSize: 10, letterSpacing: '.06em', textTransform: 'uppercase', color: COLOR[d], marginBottom: 8 }}>{LABEL[d]}</div>
              {contacts.length ? contacts.map(([resid, occ], i) => (
                <div key={resid} style={{ display: 'grid', gridTemplateColumns: '50px 1fr 42px', gap: 6, alignItems: 'center', margin: '4px 0' }}>
                  <span style={{ fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--ink-soft)', textAlign: 'right' }}>{resid}</span>
                  <div style={{ background: 'var(--paper-3)', borderRadius: 3, height: 11, overflow: 'hidden' }}>
                    <div className="bar" style={{ width: inView ? `${(occ / max) * 100}%` : '0%', height: '100%', background: COLOR[d], borderRadius: 3, transitionDelay: `${i * 25}ms` }} />
                  </div>
                  <span style={{ fontFamily: 'var(--mono)', fontSize: 10, color: 'var(--ink-faint)' }}>{occ}%</span>
                </div>
              )) : <p style={{ fontSize: 12, color: 'var(--ink-faint)' }}>No sustained contacts.</p>}
            </div>
          )
        })}
      </div>
    </div>
  )
}

export default function MD() {
  const md = useMd()
  const { reg } = useRegister()
  const [playheadNs, setPlayheadNs] = useState(0)

  const series = (metric: keyof MdSeries, yi: number): ChartLine[] =>
    DRUGS.map((d) => ({
      label: LABEL[d],
      color: COLOR[d],
      pts: (md.data?.series[d]?.[metric] ?? [])
        .filter((p) => p[0] != null && p[yi] != null)
        .map((p) => [p[0] as number, p[yi] as number] as [number, number]),
    }))

  return (
    <div className="wrap" style={{ padding: '56px 0' }}>
      <div className="eyebrow">Tool 03</div>
      <h1 style={{ fontSize: 'clamp(34px,5vw,60px)', fontWeight: 380, marginTop: 12 }}>Molecular Dynamics</h1>
      <p style={{ color: 'var(--ink-soft)', maxWidth: 720, lineHeight: 1.65, margin: '14px 0 0' }}>
        {say(reg,
          '50 ns simulations of three candidates with the dengue NS5 polymerase. Each drug starts about 30 Angstrom away in solvent, so these are unbiased association runs (does the drug find and hold a site?), not bound-pose-stability runs.',
          '50 ns all-atom MD (AMBER99SB-ILDN + GAFF2, TIP3P, 300 K) of three candidates with DENV NS5 (PDB 5CCV). The ligand was not started in the docked pose; it begins ~30 A away in solvent, so these are unbiased association simulations. A single 50 ns run is anecdotal, not a measure of affinity.')}
      </p>
      <div style={{ background: 'var(--paper-2)', border: '1px solid var(--line)', borderRadius: 12, padding: '14px 18px', margin: '18px 0 8px', fontSize: 14, color: 'var(--ink-soft)', lineHeight: 1.6, maxWidth: 760 }}>
        Celecoxib associates at about 3 ns and stays; methotrexate associates at about 14 ns and remains mobile; dasabuvir never forms a stable bound pose within 50 ns.
      </div>
      <MdAnimator onTime={setPlayheadNs} />

      {!md.data && <p className="mono" style={{ marginTop: 20 }}>Loading simulation data...</p>}

      {md.data && (
        <div style={{ overflowX: 'auto', marginTop: 18 }}>
          <table style={{ borderCollapse: 'collapse', fontSize: 13, minWidth: 640 }}>
            <thead>
              <tr>
                {['Drug', 'Protein RMSD (Å)', 'Ligand RMSD (Å)', 'Associates (ns)', 'Rg (Å)', 'H-bonds', 'Min dist (Å)', 'Contact res >50%', 'Avg contacts'].map((h) => (
                  <th key={h} style={{ textAlign: h === 'Drug' ? 'left' : 'right', padding: '8px 14px', fontFamily: 'var(--mono)', fontSize: 10, letterSpacing: '.06em', textTransform: 'uppercase', color: 'var(--ink-faint)', borderBottom: '1px solid var(--line)', whiteSpace: 'nowrap' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {md.data.summary.map((r) => (
                <tr key={r.Drug} style={{ borderBottom: '1px solid var(--line)' }}>
                  <td style={{ padding: '9px 14px', fontFamily: 'var(--serif)', fontSize: 16 }}>{r.Drug}</td>
                  <td style={tdR}>{r.Prot_RMSD_avg} ± {r.Prot_RMSD_std}</td>
                  <td style={tdR}>{r.Lig_RMSD_avg === 'no stable pose' ? 'no stable pose' : `${r.Lig_RMSD_avg} ± ${r.Lig_RMSD_std}`}</td>
                  <td style={tdR}>{r.Assoc_ns}</td>
                  <td style={tdR}>{r.Rg_avg}</td>
                  <td style={tdR}>{r.HBonds_avg} ± {r.HBonds_std}</td>
                  <td style={tdR}>{r.MinDist_avg}</td>
                  <td style={tdR}>{r.ContactRes_gt50pct}</td>
                  <td style={tdR}>{r.Contacts_avg}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {md.data && (
        <>
          <ChartBlock title="Protein backbone RMSD" caption="How far the protein drifts from its starting shape over time. A low, flat line means the protein stayed stable through the run.">
            <MultiLineChart lines={series('rmsd', 1)} xLabel="time (ns)" yLabel="RMSD (Å)" yMin={0} playheadX={playheadNs} />
          </ChartBlock>
          <ChartBlock title="Ligand RMSD vs its bound pose" caption="Once a drug settles into a site, how much its pose wobbles, measured against that drug's own bound pose. Dasabuvir never settles, so it has none.">
            <MultiLineChart lines={series('rmsd', 2)} xLabel="time (ns)" yLabel="RMSD (Å)" yMin={0} playheadX={playheadNs} />
          </ChartBlock>
          <ChartBlock title="Ligand-protein minimum distance" caption="The headline of these runs: each drug starts about 30 Å away and either finds the protein (distance drops toward 2 Å) or does not. Celecoxib and methotrexate associate; dasabuvir stays far.">
            <MultiLineChart lines={series('mindist', 1)} xLabel="time (ns)" yLabel="min distance (Å)" yMin={0} playheadX={playheadNs} />
          </ChartBlock>
          <ChartBlock title="Drug-protein hydrogen bonds" caption="Hydrogen bonds between the drug and the protein over time. More sustained bonds indicate a tighter grip once bound.">
            <MultiLineChart lines={series('hbonds', 1)} xLabel="time (ns)" yLabel="H-bonds" yMin={0} playheadX={playheadNs} />
          </ChartBlock>
          <ChartBlock title="Per-residue flexibility (RMSF)" caption="Which parts of the protein move most. Peaks are flexible loops, troughs the rigid core. Similar across the three runs, as expected for the same protein.">
            <MultiLineChart lines={series('rmsf', 1)} xLabel="residue" yLabel="RMSF (Å)" yMin={0} />
          </ChartBlock>
          <ChartBlock title="Atom-atom contacts" caption="Close contacts (within 4.5 Å) between drug and protein over time. The jump from zero marks association; a sustained high count means a tight, persistent interface.">
            <MultiLineChart lines={series('ncontacts', 1)} xLabel="time (ns)" yLabel="contacts (< 4.5 Å)" yMin={0} playheadX={playheadNs} />
          </ChartBlock>
          <TopContacts md={md.data} />
        </>
      )}
    </div>
  )
}
