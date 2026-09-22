import { describe, it, expect } from 'vitest'
import { decodeTraj, frameSpan, lerpFrame, nearestFrame, trajReadout, chainSegments, ligandCentroids, trailSegments, type MdTrajMeta } from './mdTraj'

// Two frames, three residues, two ligand atoms. Residue 2 sits 10 A from residue 1: a chain break.
const meta: MdTrajMeta = {
  drug: 'test', frames: 2, dt_ns: 0.25, scale: 100, n_residues: 3, n_ligand_atoms: 2,
  ligand_elements: ['C', 'N'], ligand_bonds: [[0, 1]], secondary_structure: 'H-E',
  min_dist: [20, 3], n_contacts: [0, 12], contacts: [[], [0, 1]],
  hbonds: [[], [[1, 0, 0, 0]]],
  image_jumps: [],
}
const ca = [
  [0, 0, 0], [3.8, 0, 0], [13.8, 0, 0], // frame 0
  [0, 1, 0], [3.8, 1, 0], [13.8, 1, 0], // frame 1
].flat()
const lig = [
  [20, 0, 0], [22, 0, 0], // frame 0
  [10, 0, 0], [12, 0, 0], // frame 1
].flat()

function encode(vals: number[], scale: number): ArrayBuffer {
  const buf = new ArrayBuffer(vals.length * 2)
  const view = new DataView(buf)
  vals.forEach((v, i) => view.setInt16(i * 2, Math.round(v * scale), true))
  return buf
}
const traj = decodeTraj(meta, encode([...ca, ...lig], 100))

describe('decodeTraj', () => {
  it('splits the buffer into C-alpha and ligand coordinates in Angstrom', () => {
    Array.from(traj.ca).forEach((v, i) => expect(v).toBeCloseTo(ca[i], 5))
    Array.from(traj.lig).forEach((v, i) => expect(v).toBeCloseTo(lig[i], 5))
  })
  it('rejects a buffer whose size does not match the header', () => {
    expect(() => decodeTraj(meta, encode([1, 2, 3], 100))).toThrow(/expected 30 values, got 3/)
  })
})

describe('frame timing', () => {
  it('maps time to the bracketing frames and a blend fraction', () => {
    expect(frameSpan(traj, 0)).toEqual({ i0: 0, i1: 0, f: 0 })
    expect(frameSpan(traj, 0.1)).toEqual({ i0: 0, i1: 1, f: 0.4 })
    expect(frameSpan(traj, 5)).toEqual({ i0: 1, i1: 1, f: 0 })
    expect(frameSpan(traj, -1)).toEqual({ i0: 0, i1: 0, f: 0 })
  })
  it('picks the nearest saved frame', () => {
    expect(nearestFrame(traj, 0.1)).toBe(0)
    expect(nearestFrame(traj, 0.2)).toBe(1)
    expect(nearestFrame(traj, 99)).toBe(1)
  })
  it('interpolates coordinates linearly between frames', () => {
    const out = new Float32Array(6)
    lerpFrame(traj.lig, 6, { i0: 0, i1: 1, f: 0.5 }, out)
    expect(Array.from(out)).toEqual([15, 0, 0, 17, 0, 0])
  })
})

describe('trajReadout', () => {
  it('reports the nearest frame values computed from the trajectory', () => {
    expect(trajReadout(traj, 0.24)).toEqual({ tNs: 0.24, distance: 3, hbonds: 1, ncontacts: 12 })
  })
})

describe('chainSegments', () => {
  it('splits the backbone where consecutive C-alphas are too far apart to be bonded', () => {
    expect(chainSegments(traj)).toEqual([[0, 2], [2, 3]])
  })
})

describe('ligandCentroids', () => {
  it('averages the ligand atoms per frame', () => {
    expect(Array.from(ligandCentroids(traj))).toEqual([21, 0, 0, 11, 0, 0])
  })
})

describe('periodic image switches', () => {
  const jumpy: MdTrajMeta = { ...meta, frames: 4, image_jumps: [2] }
  it('snaps to the nearer frame instead of sliding the drug across a switch', () => {
    expect(frameSpan(jumpy, 0.3)).toEqual({ i0: 1, i1: 1, f: 0 }) // 1.2 frames: blend 1 -> 2 would cross
    expect(frameSpan(jumpy, 0.45)).toEqual({ i0: 2, i1: 2, f: 0 }) // 1.8 frames: nearer to 2
    expect(frameSpan(jumpy, 0.55)).toEqual({ i0: 2, i1: 3, f: 0.2 }) // no switch between 2 and 3
  })
  it('leaves the path line unbroken except at switches', () => {
    expect(Array.from(trailSegments(jumpy))).toEqual([0, 1, 2, 3])
  })
})
