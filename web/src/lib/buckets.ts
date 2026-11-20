import type { FieldPoint } from '../data/types'

export interface Bucket {
  key: string
  label: string
  color: string
}

export const BUCKETS: Record<string, Bucket> = {
  nucleoside: { key: 'nucleoside', label: 'Nucleoside / polymerase blockers', color: '#2E7D5B' },
  hcvdaa: { key: 'hcvdaa', label: 'HCV direct-acting antivirals', color: '#A8492B' },
  protease: { key: 'protease', label: 'HIV protease inhibitors', color: '#A8742C' },
  dengue: { key: 'dengue', label: 'Published dengue leads', color: '#2C6E6B' },
  repurpose: { key: 'repurpose', label: 'Other repurposing leads', color: '#5B5470' },
  control: { key: 'control', label: 'Controls / negatives', color: '#8A8273' },
}

const CAT2BUCKET: Record<string, string> = {
  A_RdRp_Inhibitors: 'nucleoside',
  C_Nucleoside_Analogs: 'nucleoside',
  K_More_Nucleosides: 'nucleoside',
  I_HCV_NS3_Protease: 'hcvdaa',
  J_HCV_NS5A: 'hcvdaa',
  F_Protease_Inhibitors: 'protease',
  B_Published_Dengue: 'dengue',
  M_Arbovirus_Activity: 'repurpose',
  E_Tropical_Disease: 'repurpose',
  R_More_Tropical: 'repurpose',
  D_Host_Directed: 'repurpose',
  L_Broad_Antivirals: 'repurpose',
  N_Immune_Modulators: 'repurpose',
  H_Negative_Controls: 'control',
  Q_More_Negatives: 'control',
  O_Entry_Inhibitors: 'control',
}

export const bucketOf = (p: { category: string }): Bucket => BUCKETS[CAT2BUCKET[p.category] ?? 'repurpose']

export function insight(p: FieldPoint): string {
  if (p.name.toLowerCase() === 'sofosbuvir')
    return 'Included on purpose as a known-active control to test the method, not as a discovery.'
  if (p.mw >= 700)
    return 'Strong raw Vina score, but high molecular weight yields low ligand efficiency—likely a size-dependent scoring artefact.'
  if (p.le !== null && p.le >= 0.27)
    return 'High ligand efficiency relative to molecular size despite a modest raw docking score; merits closer inspection.'
  if (p.dl === 1 && p.vina <= -7)
    return 'Drug-like and binds well. A candidate worth following up.'
  if (p.dl === 1)
    return 'Drug-like, with balanced binding. A realistic lead.'
  return 'A mid-field candidate: worth noting, not a standout.'
}

export const AXIS = {
  plain: {
    x: 'Binding strength',
    y: 'Efficiency per atom',
    body: 'Further right indicates stronger predicted binding affinity. Higher up indicates greater ligand efficiency per heavy atom. Larger points represent heavier molecules, which often dominate raw docking scores—hence the dual-metric view.',
  },
  sci: {
    x: 'AutoDock Vina (kcal/mol)',
    y: 'Ligand efficiency',
    body: 'X = best AutoDock Vina score (more negative is stronger). Y = ligand efficiency (|Vina| / heavy atoms). Dot size scales with heavy-atom count, so heavier molecules are bigger. The green ring marks drug-like (MW 250 to 600).',
  },
}
