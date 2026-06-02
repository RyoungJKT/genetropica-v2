import { useConservation } from '../data/api'
import { useRegister, say } from '../state/register'
import { ConservationTrack } from '../components/ConservationTrack'

export default function Conservation() {
  const c = useConservation()
  const { reg } = useRegister()
  const data = c.data
  const ref = 'DENV-2'
  const identity = data?.identity?.[ref] ?? {}
  const viruses = Object.keys(identity).filter((v) => v !== ref).sort((a, b) => identity[b] - identity[a])
  const mw = data?.mann_whitney

  return (
    <div className="wrap" style={{ padding: '56px 0' }}>
      <div className="eyebrow">Tool 05</div>
      <h1 style={{ fontSize: 'clamp(34px,5vw,60px)', fontWeight: 380, marginTop: 12 }}>Conservation</h1>
      <p style={{ color: 'var(--ink-soft)', maxWidth: 720, lineHeight: 1.65, margin: '14px 0 0' }}>
        {say(reg,
          'How conserved the dengue NS5 polymerase is, position by position and across related viruses. A site that stays the same across many viruses is harder for the virus to mutate away, so a drug aimed there may be more durable.',
          'ConSurf conservation grades (1 = variable, 9 = conserved) along DENV NS5, plus cross-flavivirus sequence identity. Higher conservation at a target site suggests lower mutational escape and broader-spectrum potential.')}
      </p>

      {!data && <p className="mono" style={{ marginTop: 20 }}>Loading conservation data...</p>}

      {data && (
        <>
          <div style={{ marginTop: 32 }}>
            <h3 style={{ fontSize: 22 }}>Conservation along the protein</h3>
            <p style={{ fontSize: 13.5, color: 'var(--ink-soft)', margin: '4px 0 12px', maxWidth: 760 }}>
              Each position of NS5, shaded from variable to conserved. The catalytic residues (marked) sit in highly conserved regions.
            </p>
            <ConservationTrack grades={data.grades} keyResidues={data.key_residues.map((k) => k.residue_number)} />
          </div>

          <div style={{ marginTop: 36 }}>
            <h3 style={{ fontSize: 22 }}>NS5 across the flavivirus family</h3>
            <p style={{ fontSize: 13.5, color: 'var(--ink-soft)', margin: '4px 0 14px', maxWidth: 760 }}>
              Sequence identity of dengue (DENV-2) NS5 to other viruses. The flaviviruses are 50 to 73% identical; hepatitis C (HCV) is only ~10%, a distant relative, which is exactly why sofosbuvir (an HCV drug) is used here as a control, not a candidate.
            </p>
            {viruses.map((v) => (
              <div key={v} style={{ display: 'flex', alignItems: 'center', gap: 12, margin: '8px 0' }}>
                <span style={{ width: 64, fontSize: 13, color: 'var(--ink-soft)' }}>{v}</span>
                <div style={{ flex: 1, maxWidth: 520, height: 14, background: 'var(--paper-3)', borderRadius: 100, overflow: 'hidden' }}>
                  <div style={{ height: '100%', width: `${identity[v]}%`, background: v === 'HCV' ? 'var(--clay)' : 'var(--green)', borderRadius: 100 }} />
                </div>
                <span style={{ fontFamily: 'var(--mono)', fontSize: 12, width: 48, textAlign: 'right' }}>{identity[v]}%</span>
              </div>
            ))}
          </div>

          {mw && (
            <div style={{ marginTop: 36 }}>
              <h3 style={{ fontSize: 22 }}>Are the binding-site residues more conserved?</h3>
              <div style={{ background: 'var(--paper-2)', border: '1px solid var(--line)', borderRadius: 12, padding: '16px 18px', marginTop: 10, maxWidth: 760, fontSize: 14, color: 'var(--ink-soft)', lineHeight: 1.6 }}>
                The {mw.n_binding} binding-site residues average a conservation grade of <b>{mw.binding_mean}</b>, versus <b>{mw.nonbinding_mean}</b> for the rest of the protein, so they are more conserved. But the difference is <b>not statistically significant</b> (Mann-Whitney p = {mw.p_value}), reported honestly given the small number of binding residues.
              </div>
            </div>
          )}

          <div style={{ marginTop: 36 }}>
            <h3 style={{ fontSize: 22 }}>Key catalytic residues</h3>
            <div style={{ border: '1px solid var(--line)', borderRadius: 14, overflow: 'hidden', marginTop: 12, background: 'var(--paper)', maxWidth: 520 }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13.5 }}>
                <thead>
                  <tr>
                    {['Residue', 'Amino acid', 'Conserved across viruses'].map((h, i) => (
                      <th key={h} style={{ textAlign: i === 0 ? 'left' : 'right', padding: '9px 14px', fontFamily: 'var(--mono)', fontSize: 10, letterSpacing: '.06em', textTransform: 'uppercase', color: 'var(--ink-faint)', borderBottom: '1px solid var(--line)' }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {data.key_residues.map((k) => (
                    <tr key={k.residue_number} style={{ borderBottom: '1px solid var(--line)' }}>
                      <td style={{ padding: '9px 14px', fontFamily: 'var(--mono)' }}>{k.residue_number}</td>
                      <td style={{ padding: '9px 14px', textAlign: 'right', fontFamily: 'var(--mono)' }}>{k.reference_aa}</td>
                      <td style={{ padding: '9px 14px', textAlign: 'right', fontFamily: 'var(--mono)', color: k.conservation_pct >= 90 ? 'var(--green)' : 'var(--ink-soft)' }}>{k.conservation_pct}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
