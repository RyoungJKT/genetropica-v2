import { useRegister } from '../state/register'

export function RegisterToggle() {
  const { reg, setReg } = useRegister()
  return (
    <div
      style={{
        display: 'inline-flex',
        border: '1px solid var(--line)',
        borderRadius: 100,
        overflow: 'hidden',
        fontFamily: 'var(--mono)',
        fontSize: 10.5,
        letterSpacing: '.06em',
        textTransform: 'uppercase',
        cursor: 'pointer',
      }}
    >
      {(['plain', 'sci'] as const).map((r) => (
        <span
          key={r}
          onClick={() => setReg(r)}
          style={{
            padding: '8px 13px',
            color: reg === r ? 'var(--paper)' : 'var(--ink-faint)',
            background: reg === r ? 'var(--green)' : 'transparent',
          }}
        >
          {r === 'plain' ? 'Plain English' : 'Scientific'}
        </span>
      ))}
    </div>
  )
}
