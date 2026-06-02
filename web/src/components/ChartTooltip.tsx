import type { ReactNode } from 'react'

/** Floating, cursor-following tooltip for charts (Plotly-style). Rendered fixed; pass page coords. */
export function ChartTooltip({ x, y, children }: { x: number; y: number; children: ReactNode }) {
  const vw = typeof window !== 'undefined' ? window.innerWidth : 1200
  const vh = typeof window !== 'undefined' ? window.innerHeight : 800
  const flipX = x > vw - 220
  const flipY = y > vh - 80
  return (
    <div
      style={{
        position: 'fixed',
        left: flipX ? undefined : x + 14,
        right: flipX ? vw - x + 14 : undefined,
        top: flipY ? undefined : y + 14,
        bottom: flipY ? vh - y + 14 : undefined,
        zIndex: 70,
        pointerEvents: 'none',
        background: 'var(--ink)',
        color: 'var(--paper)',
        borderRadius: 8,
        padding: '7px 11px',
        fontFamily: 'var(--mono)',
        fontSize: 11.5,
        lineHeight: 1.5,
        boxShadow: '0 8px 24px rgba(28,26,23,.3)',
        whiteSpace: 'nowrap',
      }}
    >
      {children}
    </div>
  )
}
