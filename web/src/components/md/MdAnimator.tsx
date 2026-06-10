import { useEffect, useRef, useState } from 'react'
import { useMd } from '../../data/api'
import { MdScene } from './MdScene'
import { frameReadout, DURATION_NS } from '../../lib/mdMotion'

const DRUGS = ['celecoxib', 'methotrexate', 'dasabuvir'] as const
type Drug = (typeof DRUGS)[number]
const LABEL: Record<Drug, string> = { celecoxib: 'Celecoxib', methotrexate: 'Methotrexate', dasabuvir: 'Dasabuvir' }
const ACCENT: Record<Drug, string> = { celecoxib: '#1F5740', methotrexate: '#A8492B', dasabuvir: '#A8742C' }
const SPEED_NS_PER_SEC = 12 // about 4 s for a full 50 ns pass

function prefersReducedMotion(): boolean {
  return typeof window !== 'undefined' && !!window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
}

export function MdAnimator({ onTime }: { onTime?: (tNs: number) => void }) {
  const md = useMd()
  const reduced = prefersReducedMotion()
  const isMobile = typeof window !== 'undefined' && window.innerWidth < 760
  const [drug, setDrug] = useState<Drug>('celecoxib')
  const [playing, setPlaying] = useState(!reduced)
  const [tNs, setTNs] = useState(reduced ? DURATION_NS * 0.5 : 0)
  const tNsRef = useRef(tNs)
  const rafRef = useRef(0)
  const lastTs = useRef(0)
  const lastEmit = useRef(-1)

  useEffect(() => {
    tNsRef.current = tNs
    if (onTime && Math.abs(tNs - lastEmit.current) >= 0.5) {
      lastEmit.current = tNs
      onTime(tNs)
    }
  }, [tNs, onTime])

  useEffect(() => {
    if (!playing) return
    lastTs.current = 0
    const step = (ts: number) => {
      if (!lastTs.current) lastTs.current = ts
      const dt = (ts - lastTs.current) / 1000
      lastTs.current = ts
      setTNs((prev) => {
        const next = prev + dt * SPEED_NS_PER_SEC
        return next >= DURATION_NS ? 0 : next
      })
      rafRef.current = requestAnimationFrame(step)
    }
    rafRef.current = requestAnimationFrame(step)
    return () => cancelAnimationFrame(rafRef.current)
  }, [playing])

  const series = md.data?.series[drug]
  if (!md.data || !series) {
    return (
      <div className="mono" style={{ height: 360, display: 'grid', placeItems: 'center', color: 'var(--ink-faint)' }}>
        Loading simulation...
      </div>
    )
  }
  const readout = frameReadout(series, tNs)

  return (
    <div style={{ marginTop: 18, border: '1px solid var(--line)', borderRadius: 16, overflow: 'hidden', background: 'var(--paper)' }}>
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', padding: '12px 14px', borderBottom: '1px solid var(--line)' }}>
        {DRUGS.map((d) => (
          <button
            key={d}
            onClick={() => setDrug(d)}
            style={{
              fontFamily: 'var(--mono)', fontSize: 11, letterSpacing: '.04em', textTransform: 'uppercase',
              padding: '6px 12px', borderRadius: 999, cursor: 'pointer',
              border: `1px solid ${drug === d ? ACCENT[d] : 'var(--line)'}`,
              background: drug === d ? ACCENT[d] : 'transparent',
              color: drug === d ? '#fff' : 'var(--ink-soft)',
            }}
          >
            {LABEL[d]}
          </button>
        ))}
      </div>

      <div style={{ position: 'relative', height: isMobile ? 300 : 420, background: 'radial-gradient(circle at 50% 38%, var(--paper-2), var(--paper))' }}>
        <MdScene series={series} tNsRef={tNsRef} accent={ACCENT[drug]} reducedNodes={isMobile} />
        <div style={{ position: 'absolute', left: 14, bottom: 12, fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--ink-soft)', lineHeight: 1.5, background: 'color-mix(in srgb, var(--paper) 72%, transparent)', borderRadius: 8, padding: '6px 10px' }}>
          <div>t = {readout.tNs.toFixed(1)} ns</div>
          <div>min dist = {Number.isFinite(readout.distance) ? `${readout.distance.toFixed(1)} A` : '-'}</div>
          <div>H-bonds = {readout.hbonds} &nbsp; contacts = {readout.ncontacts}</div>
        </div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '12px 14px', borderTop: '1px solid var(--line)' }}>
        <button
          onClick={() => setPlaying((p) => !p)}
          style={{ fontFamily: 'var(--mono)', fontSize: 12, padding: '6px 14px', borderRadius: 8, border: '1px solid var(--line)', background: 'var(--paper-2)', cursor: 'pointer', color: 'var(--ink)' }}
        >
          {playing ? 'Pause' : 'Play'}
        </button>
        <input
          type="range" min={0} max={DURATION_NS} step={0.25} value={tNs}
          onChange={(e) => { setPlaying(false); setTNs(parseFloat(e.target.value)) }}
          aria-label="Scrub simulation time"
          style={{ flex: 1, accentColor: ACCENT[drug] }}
        />
        <span style={{ fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--ink-faint)', minWidth: 70, textAlign: 'right' }}>
          {tNs.toFixed(1)} / {DURATION_NS} ns
        </span>
      </div>

      <p style={{ fontSize: 12, color: 'var(--ink-faint)', lineHeight: 1.55, margin: 0, padding: '0 14px 14px' }}>
        Stylized view. The approach distance and timing, per-residue flexibility, H-bonds and contacts are taken frame-by-frame from the real 50 ns simulation. The protein's shape and the drug's exact 3D path are illustrative; the full atomic trajectory was not stored. Schematic, not to scale.
      </p>
    </div>
  )
}
