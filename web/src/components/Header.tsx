import { useState, type CSSProperties } from 'react'
import { NavLink } from 'react-router-dom'
import { RegisterToggle } from './RegisterToggle'
import { useIsMobile } from '../lib/useIsMobile'

const LINKS: [string, string][] = [
  ['/diseases', 'Diseases'],
  ['/explore', 'Candidates'],
  ['/binding', 'Binding'],
  ['/md', 'Dynamics'],
  ['/admet', 'ADMET'],
  ['/conservation', 'Conservation'],
  ['/escape', 'Escape'],
  ['/insights', 'Insights'],
  ['/methods', 'Methods'],
  ['/validation', 'Validation'],
]

const linkStyle = (isActive: boolean): CSSProperties => ({
  fontFamily: 'var(--mono)',
  fontSize: 10.5,
  letterSpacing: '.1em',
  textTransform: 'uppercase',
  color: isActive ? 'var(--green)' : 'var(--ink-soft)',
  fontWeight: isActive ? 600 : 400,
  whiteSpace: 'nowrap',
})

export function Header() {
  const isMobile = useIsMobile()
  const [open, setOpen] = useState(false)

  return (
    <header style={{ position: 'sticky', top: 0, zIndex: 30, backdropFilter: 'blur(8px)', background: 'rgba(244,240,230,.72)', borderBottom: '1px solid var(--line)' }}>
      <div className="wrap" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 16, minHeight: 62, padding: '8px 0', flexWrap: isMobile ? 'nowrap' : 'wrap' }}>
        <a href="/" style={{ fontFamily: 'var(--serif)', fontSize: 21, color: 'var(--ink)' }}>
          <b>GeneTropica</b>
        </a>
        {isMobile ? (
          <button onClick={() => setOpen((o) => !o)} aria-label="Menu" aria-expanded={open} style={{ background: 'transparent', border: '1px solid var(--line)', borderRadius: 10, padding: '7px 12px', cursor: 'pointer', fontFamily: 'var(--mono)', fontSize: 15, color: 'var(--ink)', lineHeight: 1 }}>
            {open ? '✕' : '☰'}
          </button>
        ) : (
          <nav style={{ display: 'flex', gap: 13, rowGap: 6, alignItems: 'center', flexWrap: 'wrap', justifyContent: 'flex-end' }}>
            {LINKS.map(([to, label]) => (
              <NavLink key={to} to={to} style={({ isActive }) => linkStyle(isActive)}>{label}</NavLink>
            ))}
            <RegisterToggle />
          </nav>
        )}
      </div>
      {isMobile && open && (
        <nav style={{ borderTop: '1px solid var(--line)', background: 'var(--paper)', padding: '6px 16px 16px', display: 'flex', flexDirection: 'column' }}>
          {LINKS.map(([to, label]) => (
            <NavLink key={to} to={to} onClick={() => setOpen(false)} style={({ isActive }) => ({ ...linkStyle(isActive), fontSize: 13, padding: '11px 2px', borderBottom: '1px solid var(--line)' })}>
              {label}
            </NavLink>
          ))}
          <div style={{ marginTop: 14 }}><RegisterToggle /></div>
        </nav>
      )}
    </header>
  )
}
