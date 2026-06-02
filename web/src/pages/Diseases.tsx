import { useRegister, say } from '../state/register'
import { TargetCards } from '../components/TargetCards'

const DISEASES = [
  { name: 'Dengue', tag: '~390M infections / year', body: 'A mosquito-borne flavivirus endemic across Indonesia. There is no specific antiviral, only supportive care, so a repurposed drug would fill a real gap.' },
  { name: 'Chikungunya', tag: 'debilitating joint pain', body: 'Another mosquito-borne virus, often causing long-lasting, disabling arthritis. No widely available approved antiviral or vaccine.' },
  { name: 'Leptospirosis', tag: 'bacterial, flood-linked', body: 'A bacterial zoonosis that spikes after flooding. New options could reduce late-stage mortality.' },
]

export default function Diseases() {
  const { reg } = useRegister()
  return (
    <>
      <div className="wrap" style={{ padding: '56px 0 0' }}>
        <div className="eyebrow">Tool 09</div>
        <h1 style={{ fontSize: 'clamp(34px,5vw,60px)', fontWeight: 380, marginTop: 12 }}>Disease Overview</h1>
        <p style={{ color: 'var(--ink-soft)', maxWidth: 760, lineHeight: 1.65, margin: '14px 0 0' }}>
          {say(reg,
            'Three neglected tropical diseases endemic to Indonesia. They affect millions but attract little new drug funding, which is what makes repurposing safe, approved medicines worthwhile here.',
            'Three neglected tropical diseases endemic to Indonesia. Repurposing is attractive because approved drugs already have established human safety, lowering the regulatory barrier; it does not imply efficacy.')}
        </p>
        <div className="rstack" style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 20, marginTop: 28 }}>
          {DISEASES.map((d) => (
            <div key={d.name} style={{ border: '1px solid var(--line)', borderRadius: 16, padding: 22, background: 'var(--paper)' }}>
              <h3 style={{ fontSize: 23, marginBottom: 4 }}>{d.name}</h3>
              <div style={{ fontFamily: 'var(--mono)', fontSize: 10, letterSpacing: '.08em', textTransform: 'uppercase', color: 'var(--clay)', marginBottom: 10 }}>{d.tag}</div>
              <p style={{ fontSize: 14, color: 'var(--ink-soft)', lineHeight: 1.6, margin: 0 }}>{d.body}</p>
            </div>
          ))}
        </div>
      </div>
      <TargetCards />
    </>
  )
}
