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

export interface Contact { res: string; num: string; chain: string; type: string; dist: number }
export interface BindingData { contacts: Contact[] }
export type BindingIndex = Record<string, string[]>

