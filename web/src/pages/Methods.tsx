import type { ReactNode } from 'react'
import { useMethods } from '../data/api'

function Block({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div style={{ marginTop: 32 }}>
      <h3 style={{ fontSize: 22, marginBottom: 10 }}>{title}</h3>
      {children}
    </div>
  )
}

const th: React.CSSProperties = { padding: '9px 12px', fontFamily: 'var(--mono)', fontSize: 10, letterSpacing: '.06em', textTransform: 'uppercase', color: 'var(--ink-faint)', borderBottom: '1px solid var(--line)', textAlign: 'left', whiteSpace: 'nowrap' }
const td: React.CSSProperties = { padding: '9px 12px', fontSize: 13, color: 'var(--ink-soft)', borderBottom: '1px solid var(--line)', whiteSpace: 'nowrap' }

const PARAMS = [
  ['Docking engine', 'AutoDock Vina 1.2.7'],
  ['Ligand preparation', 'Open Babel 3.1 + RDKit ETKDG conformers'],
  ['Search box', '25 x 25 x 25 Angstrom'],
  ['Exhaustiveness', '8'],
  ['Poses per run', '3 (energy range 3 kcal/mol)'],
  ['ML model', 'scikit-learn RandomForest'],
  ['ML features', '2048-bit Morgan fingerprint + normalised Vina score'],
  ['ML training data', '166 compounds from ChEMBL (RdRp activity)'],
  ['ML cross-validated AUC', '0.875 +/- 0.094'],
  ['ML nature', 'Target-agnostic ligand prior (same score for every target)'],
]
const SOURCES = [
  ['PubChem', 'Drug structures (canonical SMILES, resolved by name)'],
  ['ChEMBL', 'Activity data for the machine-learning prior'],
  ['RCSB PDB', 'The six protein target structures'],
  ['ConSurf', 'Per-residue evolutionary conservation'],
  ['NCBI E-utilities / PubMed', 'Keyword literature evidence'],
]
const COMPUTE = [
  ['Molecular dynamics (GROMACS, 50 ns)', 'NVIDIA A100 GPU, on Google Colab'],
  ['Docking, machine learning, ADMET, conservation', 'CPU, on Google Colab'],
]

export default function Methods() {
  const m = useMethods()
  return (
    <div className="wrap" style={{ padding: '56px 0' }}>
      <div className="eyebrow">Tool 07</div>
      <h1 style={{ fontSize: 'clamp(34px,5vw,60px)', fontWeight: 380, marginTop: 12 }}>Methods</h1>
      <p style={{ color: 'var(--ink-soft)', maxWidth: 760, lineHeight: 1.65, margin: '14px 0 0' }}>
        Exactly how the screen was run, so it is reproducible. 100 approved drugs were docked against six targets, rescored with a machine-learning prior, and filtered for drug-likeness and ADMET.
      </p>

      <Block title="Pipeline parameters">
        <div style={{ border: '1px solid var(--line)', borderRadius: 14, overflow: 'hidden', maxWidth: 640, background: 'var(--paper)' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <tbody>
              {PARAMS.map(([k, v]) => (
                <tr key={k}><td style={{ ...td, fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--ink-faint)', textTransform: 'uppercase', letterSpacing: '.04em' }}>{k}</td><td style={{ ...td, color: 'var(--ink)' }}>{v}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      </Block>

      <Block title="Per-target docking grid">
        <p style={{ fontSize: 13.5, color: 'var(--ink-soft)', margin: '0 0 12px', maxWidth: 760 }}>Grid centres sit on each target's catalytic or active site; the 25 Angstrom cubic box encloses the pocket. Publishing these makes every run reproducible.</p>
        {m.data && (
          <div style={{ border: '1px solid var(--line)', borderRadius: 14, overflow: 'auto', background: 'var(--paper)' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: 560 }}>
              <thead><tr>{['Target', 'Grid centre (x, y, z) Å', 'Box (Å)', 'Exhaustiveness', 'Modes'].map((h, i) => <th key={h} style={{ ...th, textAlign: i === 0 ? 'left' : 'right' }}>{h}</th>)}</tr></thead>
              <tbody>
                {m.data.docking.map((d) => (
                  <tr key={d.target_id}>
                    <td style={td}>{d.name}</td>
                    <td style={{ ...td, textAlign: 'right', fontFamily: 'var(--mono)', fontSize: 12 }}>({d.center.join(', ')})</td>
                    <td style={{ ...td, textAlign: 'right', fontFamily: 'var(--mono)' }}>{d.box}</td>
                    <td style={{ ...td, textAlign: 'right', fontFamily: 'var(--mono)' }}>{d.exhaustiveness}</td>
                    <td style={{ ...td, textAlign: 'right', fontFamily: 'var(--mono)' }}>{d.modes}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Block>

      <Block title="Data sources">
        <div style={{ border: '1px solid var(--line)', borderRadius: 14, overflow: 'hidden', maxWidth: 640, background: 'var(--paper)' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <tbody>{SOURCES.map(([k, v]) => (<tr key={k}><td style={{ ...td, fontFamily: 'var(--mono)', fontSize: 12, color: 'var(--ink)', whiteSpace: 'nowrap' }}>{k}</td><td style={td}>{v}</td></tr>))}</tbody>
          </table>
        </div>
      </Block>

      <Block title="Compute environment">
        <p style={{ fontSize: 13.5, color: 'var(--ink-soft)', margin: '0 0 12px', maxWidth: 760 }}>
          Every figure on this dashboard is a computed result, not a placeholder. The runs were executed on Google Colab: the heavy molecular dynamics on an NVIDIA A100 GPU, and the docking and analysis on CPUs.
        </p>
        <div style={{ border: '1px solid var(--line)', borderRadius: 14, overflow: 'hidden', maxWidth: 640, background: 'var(--paper)' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <tbody>{COMPUTE.map(([k, v]) => (<tr key={k}><td style={{ ...td, fontFamily: 'var(--mono)', fontSize: 12, color: 'var(--ink)' }}>{k}</td><td style={td}>{v}</td></tr>))}</tbody>
          </table>
        </div>
        <p style={{ fontSize: 13.5, color: 'var(--ink-soft)', margin: '14px 0 0', maxWidth: 760 }}>
          The pipeline is open source and the dengue NS5 validation can be re-run by anyone in the browser:{' '}
          <a href="https://colab.research.google.com/github/RyoungJKT/genetropica-v2/blob/main/colab/ns5_enrichment_validation.ipynb" target="_blank" rel="noopener" style={{ color: '#1F5740', borderBottom: '1px solid var(--line)', textDecoration: 'none' }}>reproduce the NS5 validation in Colab</a>.
        </p>
      </Block>

      <Block title="Documented limitations">
        <ul style={{ fontSize: 14.5, color: 'var(--ink-soft)', lineHeight: 1.7, maxWidth: 760, paddingLeft: 20 }}>
          <li>Docking under-ranks the true small-molecule NS5 inhibitors (retrospective AUC 0.37, below random).</li>
          <li>The machine-learning score is a target-agnostic prior, not a per-target prediction.</li>
          <li>Only dengue NS5 was retrospectively validated; the other five targets have no equivalent test.</li>
          <li>Literature links are keyword-based, not a trained relation extractor; weak links are tiered so they cannot inflate a candidate.</li>
          <li>The molecular dynamics are short unbiased association runs (the ligand was not started in the docked pose), reporting whether a drug binds, not binding free energy. No MM-PBSA.</li>
          <li>Sofosbuvir is included as a known-active positive control, not a discovery.</li>
        </ul>
      </Block>
    </div>
  )
}
