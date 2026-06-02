import { useState, type CSSProperties } from 'react'
import { useBindingIndex, useBinding, useTargets } from '../data/api'
import { useRegister, say } from '../state/register'
import { Mol3DViewer } from '../components/Mol3DViewer'
import type { Contact } from '../data/types'

const ORDER = ['DENV_NS5', 'DENV_NS3', 'DENV_E', 'CHIKV_nsP2', 'CHIKV_nsP1', 'LEPTO_LipL32']
const TYPE_COLOR: Record<string, string> = {
  'Hydrogen Bond': '#1F5740', Hydrophobic: '#A8742C', 'Pi-Stacking': '#5B5470', 'Salt Bridge': '#A8492B', Ionic: '#A8492B',
}
const tcol = (t: string) => TYPE_COLOR[t] ?? '#5B5470'
const pillBtn = (active: boolean): CSSProperties => ({ fontFamily: 'var(--mono)', fontSize: 11, letterSpacing: '.06em', textTransform: 'uppercase', padding: '8px 14px', borderRadius: 100, cursor: 'pointer', border: '1px solid var(--line)', background: active ? 'var(--green)' : 'var(--paper)', color: active ? 'var(--paper)' : 'var(--ink-soft)' })

export default function Binding() {
  const idx = useBindingIndex()
  const targets = useTargets()
  const { reg } = useRegister()
  const [tid, setTid] = useState('DENV_NS5')
  const [drug, setDrug] = useState<string | null>(null)
  const order = idx.data ? ORDER.filter((t) => idx.data![t]) : []
  const drugs = idx.data?.[tid] ?? []
  const cur = drug && drugs.includes(drug) ? drug : drugs[0] ?? null
  const binding = useBinding(tid, cur)
  const tName = (id: string) => targets.data?.find((t) => t.target_id === id)?.name ?? id

  const contacts = binding.data?.contacts ?? []
  const byType: Record<string, Contact[]> = {}
  for (const c of contacts) (byType[c.type] ??= []).push(c)

  return (
    <div className="wrap" style={{ padding: '56px 0' }}>
      <div className="eyebrow">Tool 02</div>
      <h1 style={{ fontSize: 'clamp(34px,5vw,60px)', fontWeight: 380, marginTop: 12 }}>3D Binding Viewer</h1>
      <p style={{ color: 'var(--ink-soft)', maxWidth: 700, lineHeight: 1.65, margin: '14px 0 24px' }}>
        {say(reg,
          'The docked shape of a drug-like candidate; drag to rotate it, with the protein residues its pose is predicted to touch listed alongside.',
          'The best docked pose (MODEL 1) of a drug-like candidate as ball-and-stick, with the chemistry-aware predicted contact residues. Drag to rotate, scroll to zoom.')}
      </p>

      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 14 }}>
        {order.map((id) => <button key={id} onClick={() => { setDrug(null); setTid(id) }} style={pillBtn(tid === id)}>{tName(id)}</button>)}
      </div>

      <div style={{ marginBottom: 20 }}>
        <label htmlFor="drugsel" style={{ display: 'block', fontFamily: 'var(--mono)', fontSize: 11, letterSpacing: '.14em', textTransform: 'uppercase', color: 'var(--clay)', marginBottom: 8 }}>
          Choose a candidate{drugs.length ? ` (${drugs.length} drug-like)` : ''}
        </label>
        <div style={{ position: 'relative', display: 'inline-block' }}>
          <select
            id="drugsel"
            value={cur ?? ''}
            onChange={(e) => setDrug(e.target.value)}
            style={{
              appearance: 'none', WebkitAppearance: 'none', MozAppearance: 'none',
              fontFamily: 'var(--serif)', fontSize: 22, fontWeight: 400,
              padding: '12px 54px 12px 20px', borderRadius: 12,
              border: '1.5px solid var(--green)', background: 'var(--paper)', color: 'var(--ink)',
              textTransform: 'capitalize', minWidth: 320, cursor: 'pointer',
              boxShadow: '0 6px 18px rgba(28,26,23,.07)',
            }}
          >
            {drugs.map((d) => <option key={d} value={d}>{d.replace(/_/g, ' ')}</option>)}
          </select>
          <span style={{ position: 'absolute', right: 18, top: '50%', transform: 'translateY(-50%)', pointerEvents: 'none', color: 'var(--green)', fontSize: 13 }}>▼</span>
        </div>
      </div>

      <div className="rstack" style={{ display: 'grid', gridTemplateColumns: '1fr 340px', gap: 24, alignItems: 'start' }}>
        <div>
          {binding.isLoading || !binding.data || !cur ? (
            <div className="mono" style={{ padding: 40 }}>Loading pose...</div>
          ) : (
            <Mol3DViewer
              receptorUrl={`${import.meta.env.BASE_URL}structures/${tid}.pdb`}
              ligandUrl={`${import.meta.env.BASE_URL}data/binding/${tid}__${cur}.mol`}
              contacts={binding.data.contacts}
            />
          )}
          <p style={{ fontSize: 12, color: 'var(--ink-faint)', fontStyle: 'italic', lineHeight: 1.5, marginTop: 12 }}>
            Predicted from the docked pose, not an experimental co-crystal structure. Contacts are detected geometrically and chemistry-aware (ionic only when the ligand carries an opposite-charge group); residue numbers follow the deposited PDB for this target.
          </p>
        </div>

        <div style={{ border: '1px solid var(--line)', borderRadius: 16, background: 'var(--paper)', padding: 20 }}>
          <h4 style={{ fontSize: 20, marginBottom: 4 }}>Predicted contacts</h4>
          <p style={{ fontSize: 12.5, color: 'var(--ink-faint)', margin: '0 0 14px' }}>{contacts.length} residues contacted by the best pose</p>
          {Object.keys(byType).length === 0 && <p className="mono" style={{ color: 'var(--ink-faint)' }}>No contacts recorded.</p>}
          {Object.entries(byType).map(([type, list]) => (
            <div key={type} style={{ marginBottom: 14 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontFamily: 'var(--mono)', fontSize: 10.5, letterSpacing: '.06em', textTransform: 'uppercase', color: tcol(type), marginBottom: 6 }}>
                <span style={{ width: 9, height: 9, borderRadius: '50%', background: tcol(type) }} />{type} ({list.length})
              </div>
              {list.map((c, i) => (
                <div key={i} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, color: 'var(--ink-soft)', padding: '3px 0 3px 17px' }}>
                  <span style={{ textTransform: 'capitalize' }}>{c.res.toLowerCase()} {c.num}<span style={{ color: 'var(--ink-faint)' }}> · chain {c.chain}</span></span>
                  <span style={{ fontFamily: 'var(--mono)', fontSize: 12 }}>{c.dist} Å</span>
                </div>
              ))}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
