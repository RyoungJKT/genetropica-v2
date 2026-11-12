import { Outlet } from 'react-router-dom'
import { Header } from './components/Header'
import { useT } from './i18n'

export default function App() {
  const { t } = useT()
  return (
    <>
      <Header />
      <main><Outlet /></main>
      <footer style={{ borderTop: '1px solid var(--line)', padding: '26px 0' }}>
        <div className="wrap">
          <div className="mono" style={{ textAlign: 'center', lineHeight: 1.7 }}>
            {t('GeneTropica · A computational drug-repurposing study')}
            {' · '}
            <a href="https://www.russellyoung.id" target="_blank" rel="noopener" style={{ textDecoration: 'underline', textUnderlineOffset: '3px' }}>Russell Young</a>
            {', 2026'}
          </div>
        </div>
      </footer>
    </>
  )
}
