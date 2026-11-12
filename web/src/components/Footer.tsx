export function Footer() {
  return (
    <footer style={{ padding: '46px 0', borderTop: '1px solid var(--line)' }}>
      <div className="wrap" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 18, flexWrap: 'wrap' }}>
        <div style={{ fontFamily: 'var(--serif)', fontSize: 18 }}>
          <a href="https://www.russellyoung.id" target="_blank" rel="noopener" style={{ textDecoration: 'underline', textUnderlineOffset: '3px' }}>Russell Young</a><br />
          <span style={{ color: 'var(--ink-faint)', fontFamily: 'var(--sans)', fontSize: 13 }}>British School Jakarta, GeneTropica</span>
        </div>
      </div>
    </footer>
  )
}
