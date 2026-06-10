import type { MdSeries } from '../data/types'

export const DURATION_NS = 50

type XY = [number, number]

// Drop null/missing points and keep [x, y] using column `yi` for y (x is always column 0).
function clean(points: (number | null)[][], yi: number): XY[] {
  const out: XY[] = []
  for (const p of points) {
    const x = p[0]
    const y = p[yi]
    if (x != null && y != null) out.push([x, y])
  }
  return out
}

// Linear interpolation of a cleaned, x-ascending series at x = q, clamped to the ends.
function interpAt(xy: XY[], q: number): number | null {
  if (!xy.length) return null
  if (q <= xy[0][0]) return xy[0][1]
  if (q >= xy[xy.length - 1][0]) return xy[xy.length - 1][1]
  for (let i = 1; i < xy.length; i++) {
    if (q <= xy[i][0]) {
      const [x0, y0] = xy[i - 1]
      const [x1, y1] = xy[i]
      const t = (q - x0) / ((x1 - x0) || 1)
      return y0 + t * (y1 - y0)
    }
  }
  return xy[xy.length - 1][1]
}

export function distanceAt(s: MdSeries, tNs: number): number {
  const v = interpAt(clean(s.mindist, 1), tNs)
  return v == null ? Infinity : v
}

export function proteinRmsdAt(s: MdSeries, tNs: number): number {
  const v = interpAt(clean(s.rmsd, 1), tNs)
  return v == null ? 0 : v
}

// Null when the run never formed a stable pose (e.g. dasabuvir has no ligand-RMSD column).
export function ligandRmsdAt(s: MdSeries, tNs: number): number | null {
  return interpAt(clean(s.rmsd, 2), tNs)
}

export function hbondsAt(s: MdSeries, tNs: number): number {
  const v = interpAt(clean(s.hbonds, 1), tNs)
  return v == null ? 0 : Math.max(0, Math.round(v))
}

export function ncontactsAt(s: MdSeries, tNs: number): number {
  const v = interpAt(clean(s.ncontacts, 1), tNs)
  return v == null ? 0 : Math.max(0, Math.round(v))
}

// rmsf value for the i-th residue (array order); clamps out-of-range indices.
export function rmsfFor(s: MdSeries, residueIndex: number): number {
  const arr = clean(s.rmsf, 1)
  if (!arr.length) return 0
  const idx = Math.max(0, Math.min(arr.length - 1, Math.floor(residueIndex)))
  return arr[idx][1]
}

export function residueCount(s: MdSeries): number {
  return clean(s.rmsf, 1).length
}

export interface MdReadout {
  tNs: number
  distance: number
  hbonds: number
  ncontacts: number
}

export function frameReadout(s: MdSeries, tNs: number): MdReadout {
  return {
    tNs,
    distance: distanceAt(s, tNs),
    hbonds: hbondsAt(s, tNs),
    ncontacts: ncontactsAt(s, tNs),
  }
}
