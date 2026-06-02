import type { ReactNode } from 'react'

export function Card({ children }: { children: ReactNode }) {
  return (
    <div style={{ border: '1px solid var(--line)', borderRadius: 16, background: 'var(--paper)', padding: 22 }}>
      {children}
    </div>
  )
}
