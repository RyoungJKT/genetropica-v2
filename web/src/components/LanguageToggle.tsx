import { useT, type Locale } from '../i18n'

const OPTIONS: [Locale, string, string][] = [
  ['en', 'EN', 'English'],
  ['id', 'ID', 'Bahasa Indonesia'],
]

export function LanguageToggle() {
  const { loc, setLoc } = useT()
  return (
    <div
      role="group"
      aria-label="Language"
      style={{
        display: 'inline-flex',
        border: '1px solid var(--line)',
        borderRadius: 100,
        overflow: 'hidden',
        fontFamily: 'var(--mono)',
        fontSize: 10.5,
        letterSpacing: '.06em',
        textTransform: 'uppercase',
      }}
    >
      {OPTIONS.map(([code, short, full]) => (
        <button
          key={code}
          type="button"
          lang={code}
          onClick={() => setLoc(code)}
          aria-pressed={loc === code}
          title={full}
          style={{
            padding: '8px 13px',
            border: 0,
            cursor: 'pointer',
            font: 'inherit',
            letterSpacing: 'inherit',
            textTransform: 'inherit',
            color: loc === code ? 'var(--paper)' : 'var(--ink-faint)',
            background: loc === code ? 'var(--green)' : 'transparent',
          }}
        >
          {short}
        </button>
      ))}
    </div>
  )
}
