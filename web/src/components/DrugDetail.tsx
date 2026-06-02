import type { ReactNode } from 'react'
import type { FieldPoint, Field, AdmetRow, Drug } from '../data/types'
import { bucketOf, insight } from '../lib/buckets'

function band(v: number) {
  if (v < 0.3) return { label: 'low', color: 'var(--green)' }
  if (v < 0.6) return { label: 'medium', color: 'var(--gold)' }
  return { label: 'high', color: 'var(--clay)' }
}

function Stat({ k, v, color }: { k: string; v: string; color?: string }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, padding: '6px 0', borderBottom: '1px solid var(--line)' }}>
      <span style={{ fontSize: 13, color: 'var(--ink-soft)' }}>{k}</span>
      <span style={{ fontFamily: 'var(--mono)', fontSize: 12, color: color ?? 'var(--ink)', textAlign: 'right', overflowWrap: 'anywhere' }}>{v}</span>
    </div>
  )
}

function H({ children }: { children: ReactNode }) {
  return <div style={{ fontFamily: 'var(--mono)', fontSize: 10, letterSpacing: '.14em', textTransform: 'uppercase', color: 'var(--ink-faint)', margin: '22px 0 8px' }}>{children}</div>
}

export function DrugDetail({ point, drug, admet, field, targetId, onClose }: { point: FieldPoint; drug?: Drug; admet?: AdmetRow; field: Field; targetId: string; onClose: () => void }) {
  const b = bucketOf(point)
  const dl = (field[targetId] ?? []).filter((p) => p.dl === 1)
  const vRank = [...dl].sort((a, c) => a.vina - c.vina).findIndex((p) => p.name === point.name)
  const lRank = [...dl].sort((a, c) => (c.le ?? 0) - (a.le ?? 0)).findIndex((p) => p.name === point.name)
  const cross = Object.entries(field)
    .map(([tid, pts]) => ({ tid, p: pts.find((x) => x.name === point.name) }))
    .filter((x): x is { tid: string; p: FieldPoint } => !!x.p)
  const strongest = cross.length ? Math.min(...cross.map((c) => c.p.vina)) : -1
  return (
    <>
      <div onClick={onClose} style={{ position: 'fixed', inset: 0, background: 'rgba(28,26,23,.32)', zIndex: 40 }} />
      <aside style={{ position: 'fixed', top: 0, right: 0, height: '100%', width: 'min(440px, 94vw)', background: 'var(--paper)', borderLeft: '1px solid var(--line)', boxShadow: '-22px 0 60px rgba(28,26,23,.2)', zIndex: 41, overflowY: 'auto', padding: '24px 26px 60px' }}>
        <button onClick={onClose} style={{ float: 'right', fontFamily: 'var(--mono)', fontSize: 10, letterSpacing: '.1em', textTransform: 'uppercase', color: 'var(--ink-soft)', background: 'transparent', border: '1px solid var(--line)', borderRadius: 100, padding: '6px 12px', cursor: 'pointer' }}>Close</button>
        <div className="eyebrow" style={{ color: b.color }}>{b.label}</div>
        <h2 style={{ fontSize: 32, textTransform: 'capitalize', marginTop: 6, lineHeight: 1.05 }}>{point.name.replace(/_/g, ' ')}</h2>
        <p style={{ color: 'var(--ink-soft)', fontSize: 14, marginTop: 6 }}>Approved for: {point.indication}</p>
        <p style={{ fontSize: 13.5, color: 'var(--ink)', lineHeight: 1.55, marginTop: 12, background: 'var(--paper-2)', borderRadius: 10, padding: '12px 14px' }}>{insight(point)}</p>

        <H>Against this target</H>
        <Stat k="Binding (Vina)" v={`${point.vina} kcal/mol`} />
        <Stat k="Ligand efficiency" v={point.le !== null ? point.le.toFixed(3) : 'n/a'} />
        <Stat k="Drug-like" v={point.dl ? 'yes (MW 250-600)' : 'no (outside band)'} color={point.dl ? 'var(--green)' : 'var(--ink-faint)'} />
        {point.dl === 1 && vRank >= 0 && <Stat k="Rank by binding" v={`#${vRank + 1} of ${dl.length} drug-like`} />}
        {point.dl === 1 && lRank >= 0 && <Stat k="Rank by efficiency" v={`#${lRank + 1} of ${dl.length} drug-like`} />}

        <H>Safety (ADMET)</H>
        {admet ? (
          <>
            <Stat k="Lipinski rule of five" v={admet.lipinski ? 'pass' : 'fail'} color={admet.lipinski ? 'var(--green)' : 'var(--clay)'} />
            <Stat k="Hepatotoxicity risk" v={`${band(admet.hepatotox).label} (${admet.hepatotox.toFixed(2)})`} color={band(admet.hepatotox).color} />
            <Stat k="hERG inhibition risk" v={`${band(admet.herg).label} (${admet.herg.toFixed(2)})`} color={band(admet.herg).color} />
            <Stat k="Oral bioavailability" v={`${Math.round(admet.bioavail * 100)}%`} />
            <Stat k="Overall ADMET" v={admet.pass ? 'pass' : 'flag'} color={admet.pass ? 'var(--green)' : 'var(--clay)'} />
          </>
        ) : (
          <p style={{ fontSize: 13, color: 'var(--ink-faint)' }}>No ADMET record.</p>
        )}

        <H>Structure</H>
        <Stat k="Molecular weight" v={`${Math.round(point.mw)} Da`} />
        <Stat k="Heavy atoms" v={`${point.ha}`} />
        {drug && drug.logp != null && <Stat k="logP" v={drug.logp.toFixed(2)} />}
        {drug?.inchikey && <Stat k="InChIKey" v={drug.inchikey} />}
        {drug?.structure_source && <Stat k="Structure source" v={drug.structure_source} />}

        <H>Binding across all targets</H>
        {cross.map((c) => {
          const w = strongest < 0 ? 0 : Math.max(6, (c.p.vina / strongest) * 100)
          return (
            <div key={c.tid} style={{ margin: '8px 0' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, color: 'var(--ink-soft)' }}>
                <span>{c.tid.replace(/_/g, ' ')}</span>
                <span style={{ fontFamily: 'var(--mono)' }}>{c.p.vina}</span>
              </div>
              <div style={{ height: 6, background: 'var(--paper-3)', borderRadius: 100, marginTop: 4, overflow: 'hidden' }}>
                <div style={{ height: '100%', width: `${w}%`, background: b.color, borderRadius: 100 }} />
              </div>
            </div>
          )
        })}
      </aside>
    </>
  )
}
