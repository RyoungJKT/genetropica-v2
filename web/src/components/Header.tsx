import { Link, NavLink } from 'react-router-dom'
import { RegisterToggle } from './RegisterToggle'

const LINKS: [string, string][] = [
  ['/explore', 'Candidates'],
  ['/binding', 'Binding'],
  ['/md', 'Dynamics'],
  ['/methods', 'Methods'],
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
        style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', height: 62 }}
      >
        <Link to="/" style={{ fontFamily: 'var(--serif)', fontSize: 21, color: 'var(--ink)' }}>
          <b>GeneTropica</b>
        </Link>
        <nav style={{ display: 'flex', gap: 22, alignItems: 'center' }}>
          {LINKS.map(([to, label]) => (
            <NavLink
              key={to}
              to={to}
              style={{
                fontFamily: 'var(--mono)',
                fontSize: 11,
                letterSpacing: '.12em',
                textTransform: 'uppercase',
                color: 'var(--ink-soft)',
              }}
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
