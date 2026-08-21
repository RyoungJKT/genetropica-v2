import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import { Ctx, STORAGE_KEY, initialLocale, type Locale } from '.'
import { ID } from './id'

/* Kept out of i18n/index.ts so that module stays component-free: every screen imports
   useT from '../i18n', and a file mixing a component with plain exports breaks Fast
   Refresh for all of them. */
export function LocaleProvider({ children }: { children: ReactNode }) {
  const [loc, setLoc] = useState<Locale>(initialLocale)

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, loc)
    } catch {
      /* ignore */
    }
    document.documentElement.lang = loc
  }, [loc])

  const t = useCallback((s: string) => (loc === 'id' ? ID[s] ?? s : s), [loc])
  const value = useMemo(() => ({ loc, setLoc, t }), [loc, t])

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}
