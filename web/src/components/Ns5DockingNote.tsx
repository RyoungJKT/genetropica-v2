import type { CSSProperties } from 'react'
import { useT } from '../i18n'

// The NS5 docking run searched a box that sat off the catalytic site, so its scores cannot rank
// drugs. Shown wherever NS5 docking scores are on screen, until the docking is re-run.
export function Ns5DockingNote({ style }: { style?: CSSProperties }) {
  const { t } = useT()
  return (
    <p role="note" style={{ fontSize: 13, color: 'var(--ink-soft)', lineHeight: 1.55, maxWidth: 760, margin: '0 0 18px', border: '1px solid var(--line)', borderRadius: 10, padding: '9px 13px', background: 'var(--paper-2)', ...style }}>
      {t('Superseded: the dengue NS5 docking scores come from a search box that missed the catalytic site, so do not use them to rank drugs until the docking is re-run.')}
    </p>
  )
}
