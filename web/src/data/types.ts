export interface Summary {
  drugs: number
  targets: number
  diseases: number
  docking_runs: number
}

export interface Target {
  target_id: string
  name: string
  disease: string
  pdb_id: string
  uniprot_id: string
  structure_source: string
  validation_status: string
}

export interface Drug {
  name: string
  category: string
  indication: string
  molecular_weight: number
  heavy_atoms: number
  logp: number
  inchikey: string
  structure_source: string
  smiles: string | null
  drugbank_id: string | null
  /** Target-agnostic ML activity prior (identical for a drug across every target). */
  ml: number | null
}

export interface FieldPoint {
  name: string
  category: string
  indication: string
  mw: number
  ha: number
  le: number | null
  vina: number
  dl: number
  admet: number
}

export type Field = Record<string, FieldPoint[]>

export interface AdmetRow {
  lipinski: number
  hepatotox: number
  herg: number
  bioavail: number
  pass: number
}

export type Admet = Record<string, AdmetRow>

export interface AdmetProfile {
  name: string
  desc: { mw: number; logp: number; tpsa: number; hbd: number; hba: number; rot: number }
  lipinski: boolean
  veber: boolean
  ghose: boolean
  egan: boolean
  esol: number
  gi: string
  bbb: string
  pains: string[]
  brenk: string[]
  dl: number
}

export interface LitRef {
  drug: string
  target: string
  pmid: string
  title: string
  rel: string
  conf: number | null
  tier: string
  /** Optional LLM review (present once scripts/llm_literature.py has been run). */
  llm_verdict?: string
  llm_rel?: string
  llm_conf?: number
  llm_note?: string
}

export interface Contact { res: string; num: string; chain: string; type: string; dist: number }
export interface BindingData { contacts: Contact[] }
export type BindingIndex = Record<string, string[]>

export type MdRow = Record<string, string>
export interface MdSeries {
  rmsd: (number | null)[][]
  hbonds: (number | null)[][]
  mindist: (number | null)[][]
  rmsf: (number | null)[][]
  ncontacts: (number | null)[][]
  contacts: number[][]
}
export interface Md {
  summary: MdRow[]
  series: Record<string, MdSeries>
}

export interface KeyResidue {
  residue_number: number
  reference_aa: string
  conservation_pct: number
  /** Per-virus amino acid at this position (DENV-1, ZIKV, HCV, ...). */
  [virus: string]: number | string
}
export interface MannWhitney {
  p_value: number
  statistic: number
  binding_mean: number
  nonbinding_mean: number
  n_binding: number
  n_nonbinding: number
  significant: boolean
}
export interface Conservation {
  grades: Record<string, number>
  identity: Record<string, Record<string, number>>
  mann_whitney: MannWhitney
  key_residues: KeyResidue[]
}

export interface Validation {
  auc: Record<string, number>
  ef: Record<string, { ef_1pct: number; ef_5pct: number; ef_10pct: number }>
  roc: Record<string, [number, number][]>
  metadata: Record<string, string | number>
  fair_auc: number
}
export interface DockParam {
  target_id: string
  name: string
  center: number[]
  box: number
  exhaustiveness: number
  modes: number
  vina: string
}
export interface Methods {
  docking: DockParam[]
}

