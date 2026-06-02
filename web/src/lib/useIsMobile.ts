import { useEffect, useState } from 'react'

/** True when the viewport is at or below `maxWidth` (default 768px). Updates on resize. */
export function useIsMobile(maxWidth = 768): boolean {
  const query = `(max-width:${maxWidth}px)`
  const [mobile, setMobile] = useState(() => typeof window !== 'undefined' && window.matchMedia(query).matches)
  useEffect(() => {
    const mq = window.matchMedia(query)
    const onChange = () => setMobile(mq.matches)
    onChange()
    mq.addEventListener('change', onChange)
    return () => mq.removeEventListener('change', onChange)
  }, [query])
  return mobile
}
