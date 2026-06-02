export function Footer() {
  return (
    <footer style={{ padding: '46px 0', borderTop: '1px solid var(--line)' }}>
      <div className="wrap" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 18, flexWrap: 'wrap' }}>
        <div style={{ fontFamily: 'var(--serif)', fontSize: 18 }}>
          Russell Young<br />
          <span style={{ color: 'var(--ink-faint)', fontFamily: 'var(--sans)', fontSize: 13 }}>British School Jakarta, GeneTropica</span>
        </div>
        <div className="mono">An honest computational screen, not a discovery claim</div>
      </div>
    </footer>
  )
}
