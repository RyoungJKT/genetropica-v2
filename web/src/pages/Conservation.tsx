import { useState } from 'react'
import { useConservation } from '../data/api'
import { ConservationTrack } from '../components/ConservationTrack'
import { ChartTooltip } from '../components/ChartTooltip'
import { useInView } from '../lib/anim'
import { useT } from '../i18n'

const VIRUSES = ['DENV-1', 'DENV-2', 'DENV-3', 'DENV-4', 'ZIKV', 'WNV', 'JEV', 'YFV', 'HCV']
const idColor = (p: number) => {
  const t = Math.max(0, Math.min(1, p / 100))
  const l = (a: number, b: number) => Math.round(a + (b - a) * t)
  return `rgb(${l(237, 31)},${l(231, 87)},${l(212, 64)})`
}

function PairwiseSection({ matrix }: { matrix: Record<string, Record<string, number>> }) {
  const { t } = useT()
  const [tip, setTip] = useState<{ x: number; y: number; title: string; value: string } | null>(null)
  const vs = VIRUSES.filter((v) => matrix[v])
  const meanPairs = (g: string[]) => {
    let s = 0, n = 0
    for (const a of g) for (const b of g) if (a !== b && matrix[a]?.[b] != null) { s += matrix[a][b]; n++ }
    return n ? s / n : 0
  }
  const flavi = vs.filter((v) => v !== 'HCV')
  const hcvMean = flavi.length ? flavi.reduce((s, f) => s + (matrix['HCV']?.[f] ?? 0), 0) / flavi.length : 0
  const cards: [string, number][] = [
    ['Dengue serotypes', meanPairs(vs.filter((v) => v.startsWith('DENV')))],
    ['All flaviviruses', meanPairs(flavi)],
    ['HCV vs flaviviruses', hcvMean],
  ]
  const cols = `66px repeat(${vs.length}, minmax(34px,1fr))`
  return (
    <div style={{ marginTop: 36 }}>
      <h3 style={{ fontSize: 22 }}>{t('Pairwise identity across the family')}</h3>
      <p style={{ fontSize: 13.5, color: 'var(--ink-soft)', margin: '4px 0 14px', maxWidth: 760 }}>
        {t('All-versus-all NS5 sequence identity. The four dengue serotypes are closely related; the broader flaviviruses share roughly half; hepatitis C is a distant outlier, which is why sofosbuvir is treated as a control rather than a candidate.')}
      </p>
      <div className="rstats" style={{ display: 'grid', gridTemplateColumns: 'repeat(3,minmax(0,200px))', gap: 12, marginBottom: 18 }}>
        {cards.map(([label, v]) => (
          <div key={label} style={{ border: '1px solid var(--line)', borderRadius: 14, padding: '14px 16px', background: 'var(--paper)' }}>
            <div style={{ fontFamily: 'var(--mono)', fontSize: 10, letterSpacing: '.06em', textTransform: 'uppercase', color: 'var(--ink-faint)' }}>{t(label)}</div>
            <div style={{ fontSize: 28, fontWeight: 380, marginTop: 6, lineHeight: 1 }}>{Math.round(v)}%</div>
          </div>
        ))}
      </div>
      <div style={{ border: '1px solid var(--line)', borderRadius: 14, overflow: 'auto', background: 'var(--paper)', padding: 6 }}>
        <div style={{ display: 'grid', gridTemplateColumns: cols, gap: 2, minWidth: 560 }}>
          <div />
          {vs.map((c) => <div key={'h' + c} style={{ fontFamily: 'var(--mono)', fontSize: 9, textAlign: 'center', color: 'var(--ink-faint)', padding: '4px 0' }}>{c}</div>)}
          {vs.flatMap((r) => [
            <div key={'r' + r} style={{ fontFamily: 'var(--mono)', fontSize: 9.5, color: 'var(--ink-soft)', display: 'flex', alignItems: 'center', justifyContent: 'flex-end', paddingRight: 6 }}>{r}</div>,
            ...vs.map((c) => {
              const val = r === c ? 100 : (matrix[r]?.[c] ?? matrix[c]?.[r] ?? 0)
              return (
                <div key={r + c} style={{ background: idColor(val), color: val / 100 > 0.52 ? 'var(--paper)' : 'var(--ink)', fontFamily: 'var(--mono)', fontSize: 9.5, textAlign: 'center', padding: '7px 0', borderRadius: 3, cursor: 'pointer' }}
                  onMouseMove={(e) => setTip({ x: e.clientX, y: e.clientY, title: `${r} vs ${c}`, value: `${Math.round(val)}% ${t('identity')}` })}
                  onMouseLeave={() => setTip(null)}>{Math.round(val)}</div>
              )
            }),
          ])}
        </div>
      </div>
      {tip && <ChartTooltip x={tip.x} y={tip.y}><div style={{ fontWeight: 600 }}>{tip.title}</div><div style={{ opacity: 0.85 }}>{tip.value}</div></ChartTooltip>}
    </div>
  )
}

function IdentityBars({ identity, viruses }: { identity: Record<string, number>; viruses: string[] }) {
  const { t } = useT()
  const [ref, inView] = useInView<HTMLDivElement>()
  return (
    <div ref={ref} style={{ marginTop: 36 }}>
      <h3 style={{ fontSize: 22 }}>{t('NS5 across the flavivirus family')}</h3>
      <p style={{ fontSize: 13.5, color: 'var(--ink-soft)', margin: '4px 0 14px', maxWidth: 760 }}>
        {t('Sequence identity of dengue (DENV-2) NS5 to other viruses. The flaviviruses are 50 to 73% identical; hepatitis C (HCV) is only ~10%, a distant relative, which is exactly why sofosbuvir (an HCV drug) is used here as a control, not a candidate.')}
      </p>
      {viruses.map((v, vi) => (
        <div key={v} style={{ display: 'flex', alignItems: 'center', gap: 12, margin: '8px 0' }}>
          <span style={{ width: 64, fontSize: 13, color: 'var(--ink-soft)' }}>{v}</span>
          <div style={{ flex: 1, maxWidth: 520, height: 14, background: 'var(--paper-3)', borderRadius: 100, overflow: 'hidden' }}>
            <div className="bar" style={{ height: '100%', width: inView ? `${identity[v]}%` : '0%', background: v === 'HCV' ? 'var(--clay)' : 'var(--green)', borderRadius: 100, transitionDelay: `${vi * 50}ms` }} />
          </div>
          <span style={{ fontFamily: 'var(--mono)', fontSize: 12, width: 48, textAlign: 'right' }}>{identity[v]}%</span>
        </div>
      ))}
    </div>
  )
}

export default function Conservation() {
  const { t } = useT()
  const c = useConservation()
  const data = c.data
  const ref = 'DENV-2'
  const identity = data?.identity?.[ref] ?? {}
  const viruses = Object.keys(identity).filter((v) => v !== ref).sort((a, b) => identity[b] - identity[a])
  const mw = data?.mann_whitney

  return (
    <div className="wrap" style={{ padding: '56px 0' }}>
      <div className="eyebrow">{t('Tool 05')}</div>
      <h1 style={{ fontSize: 'clamp(34px,5vw,60px)', fontWeight: 380, marginTop: 12 }}>{t('Conservation')}</h1>
      <p style={{ color: 'var(--ink-soft)', maxWidth: 720, lineHeight: 1.65, margin: '14px 0 0' }}>
        {t('How conserved the dengue NS5 polymerase is, position by position and across related viruses. A site that stays the same across many viruses is harder for the virus to mutate away, so a drug aimed there may be more durable.')}
      </p>

      {!data && <p className="mono" style={{ marginTop: 20 }}>{t('Loading conservation data...')}</p>}

      {data && (
        <>
          <div style={{ marginTop: 32 }}>
            <h3 style={{ fontSize: 22 }}>{t('Conservation along the protein')}</h3>
            <p style={{ fontSize: 13.5, color: 'var(--ink-soft)', margin: '4px 0 12px', maxWidth: 760 }}>
              {t('Each position of NS5, shaded from variable to conserved. The catalytic residues (marked) sit in highly conserved regions.')}
            </p>
            <ConservationTrack grades={data.grades} keyResidues={data.key_residues.map((k) => k.residue_number)} />
          </div>

          <IdentityBars identity={identity} viruses={viruses} />

          <PairwiseSection matrix={data.identity} />

          {mw && (
            <div style={{ marginTop: 36 }}>
              <h3 style={{ fontSize: 22 }}>{t('Are the binding-site residues more conserved?')}</h3>
              <div style={{ background: 'var(--paper-2)', border: '1px solid var(--line)', borderRadius: 12, padding: '16px 18px', marginTop: 10, maxWidth: 760, fontSize: 14, color: 'var(--ink-soft)', lineHeight: 1.6 }}>
                {t('The')} {mw.n_binding} {t('binding-site residues average a conservation grade of')} <b>{mw.binding_mean}</b>, {t('versus')} <b>{mw.nonbinding_mean}</b> {t('for the rest of the protein, so they are more conserved. But the difference is')} <b>{t('not statistically significant')}</b> (Mann-Whitney p = {mw.p_value}), {t('reported honestly given the small number of binding residues.')}
              </div>
            </div>
          )}

          <div style={{ marginTop: 36 }}>
            <h3 style={{ fontSize: 22 }}>{t('Key catalytic residues across viruses')}</h3>
            <p style={{ fontSize: 13.5, color: 'var(--ink-soft)', margin: '4px 0 12px', maxWidth: 760 }}>
              {t('The catalytic and active-site residues, and the amino acid each virus carries there. Differences from the dengue (DENV-2) reference are highlighted; near-total conservation across the family is what makes these sites attractive, durable drug targets.')}
            </p>
            <div style={{ border: '1px solid var(--line)', borderRadius: 14, overflow: 'auto', background: 'var(--paper)' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12.5, minWidth: 720 }}>
                <thead>
                  <tr>
                    {[t('Residue'), t('Ref'), ...VIRUSES, t('Conserved')].map((h, i) => (
                      <th key={h + i} style={{ textAlign: i === 0 ? 'left' : i === VIRUSES.length + 2 ? 'right' : 'center', padding: '9px 8px', fontFamily: 'var(--mono)', fontSize: 9.5, letterSpacing: '.04em', textTransform: 'uppercase', color: 'var(--ink-faint)', borderBottom: '1px solid var(--line)', whiteSpace: 'nowrap', position: 'sticky', top: 0, background: 'var(--paper-2)' }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {data.key_residues.map((k) => (
                    <tr key={k.residue_number} style={{ borderBottom: '1px solid var(--line)' }}>
                      <td style={{ padding: '8px', fontFamily: 'var(--mono)' }}>{k.residue_number}</td>
                      <td style={{ padding: '8px', textAlign: 'center', fontFamily: 'var(--mono)', fontWeight: 700 }}>{k.reference_aa}</td>
                      {VIRUSES.map((v) => {
                        const aa = k[v] as string | undefined
                        const mismatch = aa != null && aa !== k.reference_aa
                        return <td key={v} style={{ padding: '8px', textAlign: 'center', fontFamily: 'var(--mono)', color: mismatch ? 'var(--clay)' : 'var(--ink-soft)', fontWeight: mismatch ? 700 : 400 }}>{aa ?? '-'}</td>
                      })}
                      <td style={{ padding: '8px', textAlign: 'right', fontFamily: 'var(--mono)', color: k.conservation_pct >= 90 ? 'var(--green)' : 'var(--ink-soft)' }}>{k.conservation_pct}%</td>
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
