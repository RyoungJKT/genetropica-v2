import { useQuery } from '@tanstack/react-query'
import { decodeTraj, type MdTrajMeta } from '../lib/mdTraj'
import type { Summary, Target, Drug, Field, LitRef, BindingData, BindingIndex, Md, Conservation, Validation, Methods, Escape, Ns5Enrichment, Ns5EnrichmentCurrent } from './types'

const json = async <T>(path: string): Promise<T> => {
  const res = await fetch(`${import.meta.env.BASE_URL}data/${path}`)
  if (!res.ok) throw new Error(`failed to load ${path}: ${res.status}`)
  return res.json() as Promise<T>
}

export const useSummary = () => useQuery({ queryKey: ['summary'], queryFn: () => json<Summary>('summary.json') })
export const useTargets = () => useQuery({ queryKey: ['targets'], queryFn: () => json<Target[]>('targets.json') })
export const useDrugs = () => useQuery({ queryKey: ['drugs'], queryFn: () => json<Drug[]>('drugs.json') })
export const useField = () => useQuery({ queryKey: ['field'], queryFn: () => json<Field>('field.json') })
export const useLiterature = () => useQuery({ queryKey: ['literature'], queryFn: () => json<LitRef[]>('literature.json') })
export const useMd = () => useQuery({ queryKey: ['md'], queryFn: () => json<Md>('md.json') })
export const useMdTraj = (drug: string) =>
  useQuery({
    queryKey: ['mdTraj', drug],
    queryFn: async () => {
      const meta = await json<MdTrajMeta>(`md_traj/${drug}.json`)
      const res = await fetch(`${import.meta.env.BASE_URL}data/md_traj/${drug}.bin`)
      if (!res.ok) throw new Error(`failed to load md_traj/${drug}.bin: ${res.status}`)
      return decodeTraj(meta, await res.arrayBuffer())
    },
  })
export const useConservation = () => useQuery({ queryKey: ['conservation'], queryFn: () => json<Conservation>('conservation.json') })
export const useValidation = () => useQuery({ queryKey: ['validation'], queryFn: () => json<Validation>('validation.json') })
export const useNs5Enrichment = () => useQuery({ queryKey: ['ns5Enrichment'], queryFn: () => json<Ns5Enrichment>('ns5_enrichment.json') })
export const useNs5EnrichmentCurrent = () => useQuery({ queryKey: ['ns5EnrichmentCurrent'], queryFn: () => json<Ns5EnrichmentCurrent>('ns5_enrichment_current.json') })
export const useMethods = () => useQuery({ queryKey: ['methods'], queryFn: () => json<Methods>('methods.json') })
export const useEscape = () => useQuery({ queryKey: ['escape'], queryFn: () => json<Escape>('escape.json') })
export const useBindingIndex = () => useQuery({ queryKey: ['bindingIndex'], queryFn: () => json<BindingIndex>('binding/index.json') })
export const useBinding = (target: string, drug: string | null) =>
  useQuery({ queryKey: ['binding', target, drug], queryFn: () => json<BindingData>(`binding/${target}__${drug}.json`), enabled: !!drug })
