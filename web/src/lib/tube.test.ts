import { describe, it, expect } from 'vitest'
import { tubeIndex, tubeVertexCount, writeTube } from './tube'

describe('tube topology', () => {
  it('has one ring per centreline sample and two triangles per quad', () => {
    // 3 points, 4 samples per span -> 9 rings; 6 around -> 54 vertices
    expect(tubeVertexCount(3, 4, 6)).toBe(54)
    const idx = tubeIndex(3, 4, 6)
    expect(idx.length).toBe((9 - 1) * 6 * 6)
    expect(Math.max(...idx)).toBe(53)
  })
})

describe('writeTube', () => {
  // A straight backbone along x: every ring must be a circle of the given radius around the axis.
  const pts = new Float32Array([0, 0, 0, 4, 0, 0, 8, 0, 0])
  const radii = new Float32Array([1, 1, 2])
  const n = tubeVertexCount(3, 4, 6)
  const pos = new Float32Array(n * 3)
  const nor = new Float32Array(n * 3)
  writeTube(pts, 0, 3, radii, 4, 6, pos, nor)

  it('passes through the C-alpha positions and places rings at the right radius', () => {
    let prevX = -Infinity
    for (let ring = 0; ring < 9; ring++) {
      const seg = Math.min(1, Math.floor(ring / 4))
      const r = radii[seg] + (radii[seg + 1] - radii[seg]) * (ring / 4 - seg)
      let cx = 0
      for (let j = 0; j < 6; j++) {
        const v = (ring * 6 + j) * 3
        cx += pos[v] / 6
        expect(Math.hypot(pos[v + 1], pos[v + 2])).toBeCloseTo(r, 4)
      }
      if (ring % 4 === 0) expect(cx).toBeCloseTo(pts[(ring / 4) * 3], 4) // exactly on each C-alpha
      expect(cx).toBeGreaterThan(prevX) // and moving forward in between
      prevX = cx
    }
  })

  it('writes unit normals pointing away from the axis', () => {
    for (let v = 0; v < n; v++) {
      const k = v * 3
      expect(Math.hypot(nor[k], nor[k + 1], nor[k + 2])).toBeCloseTo(1, 4)
      expect(nor[k]).toBeCloseTo(0, 4)
      const dot = nor[k + 1] * pos[k + 1] + nor[k + 2] * pos[k + 2]
      expect(dot).toBeGreaterThan(0)
    }
  })

  it('reads a sub-range of larger coordinate and radius arrays', () => {
    const big = new Float32Array([99, 99, 99, ...pts])
    const pos2 = new Float32Array(n * 3)
    writeTube(big, 1, 3, new Float32Array([0, ...radii]), 4, 6, pos2, new Float32Array(n * 3))
    expect(Array.from(pos2)).toEqual(Array.from(pos))
  })
})
