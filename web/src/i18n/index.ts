import { createContext, useContext } from 'react'

export type Locale = 'en' | 'id'

/* Shared with the landing page, which is a separate static document on the same
   origin, so a reader's choice survives moving between the two. */
export const STORAGE_KEY = 'gt-locale'

export interface LocaleValue {
  loc: Locale
  setLoc: (l: Locale) => void
  /* Keyed by the English source string rather than by invented ids. English therefore
     needs no dictionary at all, and any string missing from the Indonesian dictionary
     falls back to English instead of rendering a raw key. */
  t: (s: string) => string
}

export const Ctx = createContext<LocaleValue>({
  loc: 'en',
  setLoc: () => {},
  t: (s) => s,
})

export function initialLocale(): Locale {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved === 'en' || saved === 'id') return saved
    /* Deliberately English-first: no navigator.language sniffing. The site is read by
       international and Indonesian audiences alike, and a machine that happens to be set
       to Indonesian is not a statement of preference. Indonesian is one click away and
       persists once chosen. */
  } catch {
    /* private browsing can throw on storage access */
  }
  return 'en'
}

export const useT = () => useContext(Ctx)
