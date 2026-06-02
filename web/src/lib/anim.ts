import { useEffect, useRef, useState, type RefObject } from 'react'

const reducedMotion = () =>
  typeof window !== 'undefined' &&
  typeof window.matchMedia === 'function' &&
  window.matchMedia('(prefers-reduced-motion: reduce)').matches

/**
 * Returns [ref, inView]. Flips to true (once) when the element scrolls into view.
 * Uses IntersectionObserver (not rAF), and falls back to true after a short delay,
 * so chart content is never left stranded at its zero/hidden state.
 */
export function useInView<T extends Element>(): [RefObject<T | null>, boolean] {
  const ref = useRef<T | null>(null)
  const [inView, setInView] = useState(false)
  useEffect(() => {
    const el = ref.current
    let io: IntersectionObserver | null = null
    if (el && typeof IntersectionObserver !== 'undefined') {
      io = new IntersectionObserver(
        (entries) => {
          if (entries.some((e) => e.isIntersecting)) {
            setInView(true)
            io?.disconnect()
          }
        },
        { threshold: 0.15, rootMargin: '0px 0px -8% 0px' },
      )
      io.observe(el)
    } else {
      setInView(true)
    }
    const fallback = setTimeout(() => setInView(true), 1200)
    return () => {
      io?.disconnect()
      clearTimeout(fallback)
    }
  }, [])
  return [ref, inView]
}

/** Counts an integer from 0 to target once `active` is true. Honors reduced-motion (jumps to target). */
export function useCountUp(target: number, active: boolean, duration = 850): number {
  const [val, setVal] = useState(0)
  useEffect(() => {
    if (!active) return
    if (reducedMotion()) {
      setVal(target)
      return
    }
    let raf = 0
    let start = 0
    const ease = (t: number) => 1 - Math.pow(1 - t, 3)
    const step = (ts: number) => {
      if (!start) start = ts
      const p = Math.min(1, (ts - start) / duration)
      setVal(Math.round(target * ease(p)))
      if (p < 1) raf = requestAnimationFrame(step)
    }
    raf = requestAnimationFrame(step)
    // Guarantee the final value even if rAF is starved (e.g. throttled tab).
    const done = setTimeout(() => setVal(target), duration + 250)
    return () => {
      cancelAnimationFrame(raf)
      clearTimeout(done)
    }
  }, [active, target, duration])
  return active ? val : 0
}
