import { useState, type CSSProperties } from 'react'
import { useField, useAdmet, useDrugs, useTargets } from '../data/api'
import { useRegister, say } from '../state/register'
import { BUCKETS, bucketOf } from '../lib/buckets'
import { DrugTable } from '../components/DrugTable'
import { DrugPanel } from '../components/DrugPanel'
import { TargetAnalysis } from '../components/TargetAnalysis'

const ORDER = ['DENV_NS5', 'DENV_NS3', 'DENV_E', 'CHIKV_nsP2', 'CHIKV_nsP1', 'LEPTO_LipL32']

const pillBtn = (active: boolean): CSSProperties => ({
  fontFamily: 'var(--mono)', fontSize: 11, letterSpacing: '.06em', textTransform: 'uppercase',
  padding: '8px 14px', borderRadius: 100, cursor: 'pointer', border: '1px solid var(--line)',
  background: active ? 'var(--green)' : 'var(--paper)', color: active ? 'var(--paper)' : 'var(--ink-soft)',
})
const inputStyle: CSSProperties = { fontFamily: 'var(--sans)', fontSize: 14, padding: '8px 14px', borderRadius: 100, border: '1px solid var(--line)', background: 'var(--paper)', color: 'var(--ink)', minWidth: 180 }
const selectStyle: CSSProperties = { fontFamily: 'var(--mono)', fontSize: 11, padding: '9px 12px', borderRadius: 100, border: '1px solid var(--line)', background: 'var(--paper)', color: 'var(--ink-soft)' }

function Toggle({ on, set, label }: { on: boolean; set: (v: boolean) => void; label: string }) {
  return <button onClick={() => set(!on)} style={pillBtn(on)}>{label}</button>
}

export default function Explore() {
  const field = useField()
  const admet = useAdmet()
  const drugs = useDrugs()
  const targets = useTargets()
  const { reg } = useRegister()
  const [tid, setTid] = useState('DENV_NS5')
  const [q, setQ] = useState('')
  const [dlOnly, setDlOnly] = useState(false)
  const [admetOnly, setAdmetOnly] = useState(false)
  const [cls, setCls] = useState('all')
  const [sel, setSel] = useState<string | null>(null)

  const tName = (id: string) => targets.data?.find((t) => t.target_id === id)?.name ?? id
  const all = field.data?.[tid] ?? []
  const order = field.data ? ORDER.filter((t) => field.data![t]) : []
  const filtered = all.filter(
    (p) =>
      (!q || p.name.toLowerCase().includes(q.toLowerCase())) &&
      (!dlOnly || p.dl === 1) &&
      (!admetOnly || p.admet === 1) &&
      (cls === 'all' || bucketOf(p).key === cls),
  )
  const selDrug = sel ? drugs.data?.find((d) => d.name === sel) : undefined
  const selAdmet = sel && admet.data ? admet.data[sel] : undefined

  return (
    <div className="wrap" style={{ padding: '56px 0' }}>
      <div className="eyebrow">Tool 01</div>
      <h1 style={{ fontSize: 'clamp(34px,5vw,60px)', fontWeight: 380, marginTop: 12 }}>Drug Explorer</h1>
      <p style={{ color: 'var(--ink-soft)', maxWidth: 680, lineHeight: 1.65, margin: '14px 0 26px' }}>
        {say(reg,
          'Every screened drug for a target, sortable and filterable. Click any drug for its full profile.',
          'All docked candidates per target, with Vina score, ligand efficiency, the drug-like band and ADMET. Click a row for the per-drug profile.')}
      </p>

      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 18 }}>
        {order.map((id) => (
          <button key={id} onClick={() => { setSel(null); setTid(id) }} style={pillBtn(tid === id)}>{tName(id)}</button>
        ))}
      </div>

      {field.data && <TargetAnalysis points={all} targetName={tName(tid)} shown={filtered.length} />}

      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'center', marginBottom: 16, marginTop: 36 }}>
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search drug..." style={inputStyle} />
        <select value={cls} onChange={(e) => setCls(e.target.value)} style={selectStyle}>
          <option value="all">All classes</option>
          {Object.values(BUCKETS).map((b) => <option key={b.key} value={b.key}>{b.label}</option>)}
        </select>
        <Toggle on={dlOnly} set={setDlOnly} label="Drug-like only" />
        <Toggle on={admetOnly} set={setAdmetOnly} label="ADMET pass only" />
        <span className="mono" style={{ color: 'var(--ink-faint)' }}>{filtered.length} of {all.length}</span>
      </div>

      {field.isLoading ? (
        <p className="mono">Loading candidates...</p>
      ) : (
        <DrugTable points={filtered} onSelect={(p) => setSel(p.name)} selected={sel ?? undefined} />
      )}

      <div style={{ marginTop: 52 }}>
        <div className="eyebrow">Drug detail</div>
        <label htmlFor="drugsel" style={{ display: 'block', fontFamily: 'var(--mono)', fontSize: 10, letterSpacing: '.1em', textTransform: 'uppercase', color: 'var(--ink-faint)', margin: '12px 0 6px' }}>Select a drug to view details</label>
        <select id="drugsel" value={sel ?? ''} onChange={(e) => setSel(e.target.value || null)} style={{ ...inputStyle, minWidth: 280, borderRadius: 12, textTransform: 'capitalize' }}>
          <option value="">Select a drug...</option>
          {[...(drugs.data ?? [])].sort((a, b) => a.name.localeCompare(b.name)).map((d) => (
            <option key={d.name} value={d.name}>{d.name}</option>
          ))}
        </select>
        {selDrug && field.data ? (
          <DrugPanel drug={selDrug} field={field.data} admet={selAdmet} order={order} tName={tName} />
        ) : (
          <p style={{ marginTop: 16, fontSize: 14, color: 'var(--ink-faint)' }}>Choose a drug above, or click a row in the table, to see its cross-target binding and ADMET profile.</p>
        )}
      </div>
    </div>
  )
}
