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

export const bucketOf = (p: FieldPoint): Bucket => BUCKETS[CAT2BUCKET[p.category] ?? 'repurpose']

export function insight(p: FieldPoint): string {
  if (p.name.toLowerCase() === 'sofosbuvir')
    return 'Included on purpose as a known-active control to test the method, not as a discovery.'
  if (p.mw >= 700)
    return "Binds hard, but it is a very large molecule, so its grip per atom is poor. Likely a size artefact more than a real lead."
  if (p.le !== null && p.le >= 0.27)
    return 'Unusually efficient for its small size, even if its raw grip is modest. The kind of profile worth a closer look.'
  if (p.dl === 1 && p.admet === 1 && p.vina <= -7)
    return 'Drug-like, passes the safety filter, and binds well. A genuine candidate to follow up.'
  if (p.dl === 1 && p.admet === 1)
    return 'Drug-like and safe-profiled, with balanced binding. A realistic lead.'
  if (p.admet === 0)
    return 'Binds reasonably, but flags on the safety filter, so it drops down the practical ranking.'
  return 'A mid-field candidate: worth noting, not a standout.'
}

export const AXIS = {
  plain: {
    x: 'Binding strength',
    y: 'Efficiency per atom',
    body: 'Further right grips the protein harder. Higher up means more grip per atom. Bigger spheres are heavier molecules. The catch: the hardest grippers are often just the biggest molecules, which is exactly why we also score efficiency.',
  },
  sci: {
    x: 'AutoDock Vina (kcal/mol)',
    y: 'Ligand efficiency',
    body: 'X = best AutoDock Vina score (more negative is stronger). Y = ligand efficiency (|Vina| / heavy atoms). Sphere depth encodes molecular weight; radius scales with heavy-atom count. Opacity encodes ADMET pass; the green ring marks drug-like (MW 250 to 600).',
  },
}
