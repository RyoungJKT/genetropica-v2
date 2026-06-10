import { describe, it, expect } from 'vitest'
import { residueNodes, ligandPos, pocketNodeIndices, POCKET } from './mdLayout'

function dist(a: [number, number, number], b: [number, number, number]) {
  return Math.hypot(a[0] - b[0], a[1] - b[1], a[2] - b[2])
}

describe('residueNodes', () => {
  it('returns the requested count and is deterministic', () => {
    const a = residueNodes(849)
    const b = residueNodes(849)
    expect(a).toHaveLength(849)
    expect(a[0].pos).toEqual(b[0].pos)
    expect(a[100].coreness).toEqual(b[100].coreness)
  })
})

describe('ligandPos and pocket', () => {
  it('sits at the pocket when distance is zero', () => {
    const p = ligandPos(0)
    expect(dist(p, POCKET)).toBeLessThan(1e-6)
  })
  it('is farther from the pocket as distance grows', () => {
    expect(dist(ligandPos(20), POCKET)).toBeGreaterThan(dist(ligandPos(2), POCKET))
  })
})

describe('pocketNodeIndices', () => {
  it('returns k indices near the pocket', () => {
    const nodes = residueNodes(849)
    const idx = pocketNodeIndices(nodes, 14)
    expect(idx).toHaveLength(14)
    expect(new Set(idx).size).toBe(14)
  })
})
