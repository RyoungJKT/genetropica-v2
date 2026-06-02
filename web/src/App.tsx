import { Outlet } from 'react-router-dom'
import { Header } from './components/Header'
import { AskAssistant } from './components/AskAssistant'

export default function App() {
  return (
    <>
      <Header />
      <main><Outlet /></main>
      <AskAssistant />
    </>
  )
}
