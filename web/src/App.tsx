import { Outlet } from 'react-router-dom'
import { Header } from './components/Header'
import { AskAssistant } from './components/AskAssistant'
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
            {t('GeneTropica · A computational drug-repurposing study · Russell Young, 2026')}
          </div>
        </div>
      </footer>
      <AskAssistant />
    </>
  )
}
