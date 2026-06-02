import { NavLink } from 'react-router-dom'
import { RegisterToggle } from './RegisterToggle'

const LINKS: [string, string][] = [
  ['/diseases', 'Diseases'],
  ['/explore', 'Candidates'],
  ['/binding', 'Binding'],
  ['/md', 'Dynamics'],
  ['/admet', 'ADMET'],
  ['/conservation', 'Conservation'],
  ['/insights', 'Insights'],
  ['/methods', 'Methods'],
  ['/validation', 'Validation'],
]

export function Header() {
  return (
    <header
      style={{
        position: 'sticky',
        top: 0,
        zIndex: 30,
        backdropFilter: 'blur(8px)',
        background: 'rgba(244,240,230,.72)',
        borderBottom: '1px solid var(--line)',
      }}
    >
      <div
        className="wrap"
        style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 16, minHeight: 62, padding: '8px 0', flexWrap: 'wrap' }}
      >
        {/* Plain anchor (not router Link) so it leaves the /app SPA and lands on the static landing page at the site root. */}
        <a href="/" style={{ fontFamily: 'var(--serif)', fontSize: 21, color: 'var(--ink)' }}>
          <b>GeneTropica</b>
        </a>
        <nav style={{ display: 'flex', gap: 13, rowGap: 6, alignItems: 'center', flexWrap: 'wrap', justifyContent: 'flex-end' }}>
          {LINKS.map(([to, label]) => (
            <NavLink
              key={to}
              to={to}
              style={({ isActive }) => ({
                fontFamily: 'var(--mono)',
                fontSize: 10.5,
                letterSpacing: '.1em',
                textTransform: 'uppercase',
                color: isActive ? 'var(--green)' : 'var(--ink-soft)',
                fontWeight: isActive ? 600 : 400,
                whiteSpace: 'nowrap',
              })}
            >
              {label}
            </NavLink>
          ))}
          <RegisterToggle />
        </nav>
      </div>
    </header>
  )
}
