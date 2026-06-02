import { useQuery } from '@tanstack/react-query'
import type { Summary, Target, Drug, Field, Admet, BindingData, BindingIndex, Md, Conservation } from './types'

const json = async <T>(path: string): Promise<T> => {
  const res = await fetch(`${import.meta.env.BASE_URL}data/${path}`)
  if (!res.ok) throw new Error(`failed to load ${path}: ${res.status}`)
  return res.json() as Promise<T>
}

export const useSummary = () => useQuery({ queryKey: ['summary'], queryFn: () => json<Summary>('summary.json') })
export const useTargets = () => useQuery({ queryKey: ['targets'], queryFn: () => json<Target[]>('targets.json') })
export const useDrugs = () => useQuery({ queryKey: ['drugs'], queryFn: () => json<Drug[]>('drugs.json') })
export const useField = () => useQuery({ queryKey: ['field'], queryFn: () => json<Field>('field.json') })
export const useAdmet = () => useQuery({ queryKey: ['admet'], queryFn: () => json<Admet>('admet.json') })
export const useMd = () => useQuery({ queryKey: ['md'], queryFn: () => json<Md>('md.json') })
export const useConservation = () => useQuery({ queryKey: ['conservation'], queryFn: () => json<Conservation>('conservation.json') })
export const useBindingIndex = () => useQuery({ queryKey: ['bindingIndex'], queryFn: () => json<BindingIndex>('binding/index.json') })
export const useBinding = (target: string, drug: string | null) =>
  useQuery({ queryKey: ['binding', target, drug], queryFn: () => json<BindingData>(`binding/${target}__${drug}.json`), enabled: !!drug })
