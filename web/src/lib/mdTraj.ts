// The real 50 ns MD trajectories, as exported by scripts/export_md_trajectory.py.

export interface MdTrajMeta {
  drug: string
  frames: number
  dt_ns: number
  scale: number // Int16 units per Angstrom in the .bin file
  n_residues: number
  n_ligand_atoms: number
  ligand_elements: string[]
  ligand_bonds: [number, number][]
  secondary_structure: string // one DSSP letter per residue: H helix, E strand, - other
  min_dist: number[] // per frame, Angstrom
  n_contacts: number[] // per frame, atom pairs within 4.5 A
  contacts: number[][] // per frame, 0-based residue indices within 4.5 A of the drug
  hbonds: [number, number, number, number][][] // per frame: [ligand atom, partner x, y, z]
  // Frames where the drug is shown next to a different periodic copy of the protein than in
  // the frame before (the box repeats in every direction), so it jumps rather than moves.
  image_jumps: number[]
}

export interface MdTraj extends MdTrajMeta {
  ca: Float32Array // frames * n_residues * 3, Angstrom
  lig: Float32Array // frames * n_ligand_atoms * 3, Angstrom
}

export function decodeTraj(meta: MdTrajMeta, buf: ArrayBuffer): MdTraj {
  const nCa = meta.frames * meta.n_residues * 3
  const nLig = meta.frames * meta.n_ligand_atoms * 3
  const got = buf.byteLength / 2
  if (got !== nCa + nLig) throw new Error(`md trajectory ${meta.drug}: expected ${nCa + nLig} values, got ${got}`)
  const view = new DataView(buf)
  const read = (offset: number, n: number) => {
    const out = new Float32Array(n)
    for (let i = 0; i < n; i++) out[i] = view.getInt16((offset + i) * 2, true) / meta.scale
    return out
  }
  return { ...meta, ca: read(0, nCa), lig: read(nCa, nLig) }
}

export interface FrameSpan {
  i0: number
  i1: number
  f: number // blend from frame i0 (0) to i1 (1)
}

export function frameSpan(traj: MdTrajMeta, tNs: number): FrameSpan {
  const last = traj.frames - 1
  const x = tNs / traj.dt_ns
  if (x <= 0) return { i0: 0, i1: 0, f: 0 }
  if (x >= last) return { i0: last, i1: last, f: 0 }
  const i0 = Math.floor(x)
  const f = Math.round((x - i0) * 1e6) / 1e6
  // Never blend across a periodic image switch: that would slide the drug through space it
  // never crossed. Show whichever real frame is nearer instead.
  if (traj.image_jumps.includes(i0 + 1)) {
    const i = f < 0.5 ? i0 : i0 + 1
    return { i0: i, i1: i, f: 0 }
  }
  return { i0, i1: i0 + 1, f }
}

// Index pairs for the drug's path line: consecutive frames, except across image switches.
export function trailSegments(traj: MdTrajMeta): Uint32Array {
  const jumps = new Set(traj.image_jumps)
  const idx: number[] = []
  for (let i = 1; i < traj.frames; i++) if (!jumps.has(i)) idx.push(i - 1, i)
  return Uint32Array.from(idx)
}

export function nearestFrame(traj: MdTrajMeta, tNs: number): number {
  return Math.max(0, Math.min(traj.frames - 1, Math.round(tNs / traj.dt_ns)))
}

// Writes the blend of two frames of a packed coordinate array into `out`.
export function lerpFrame(src: Float32Array, perFrame: number, span: FrameSpan, out: Float32Array): void {
  const a = span.i0 * perFrame
  const b = span.i1 * perFrame
  for (let k = 0; k < perFrame; k++) out[k] = src[a + k] + (src[b + k] - src[a + k]) * span.f
}

export interface TrajReadout {
  tNs: number
  distance: number
  hbonds: number
  ncontacts: number
}

export function trajReadout(traj: MdTrajMeta, tNs: number): TrajReadout {
  const i = nearestFrame(traj, tNs)
  return { tNs, distance: traj.min_dist[i], hbonds: traj.hbonds[i].length, ncontacts: traj.n_contacts[i] }
}

const MAX_CA_GAP = 4.5 // A; bonded C-alphas sit about 3.8 A apart

// [start, end) residue ranges of the backbone, split at chain breaks in the starting frame.
export function chainSegments(traj: MdTraj): [number, number][] {
  const segs: [number, number][] = []
  let start = 0
  for (let r = 1; r < traj.n_residues; r++) {
    const a = (r - 1) * 3
    const b = r * 3
    const gap = Math.hypot(traj.ca[b] - traj.ca[a], traj.ca[b + 1] - traj.ca[a + 1], traj.ca[b + 2] - traj.ca[a + 2])
    if (gap > MAX_CA_GAP) {
      segs.push([start, r])
      start = r
    }
  }
  segs.push([start, traj.n_residues])
  return segs
}

export function ligandCentroids(traj: MdTraj): Float32Array {
  const n = traj.n_ligand_atoms
  const out = new Float32Array(traj.frames * 3)
  for (let fr = 0; fr < traj.frames; fr++) {
    for (let a = 0; a < n; a++) {
      const k = (fr * n + a) * 3
      out[fr * 3] += traj.lig[k] / n
      out[fr * 3 + 1] += traj.lig[k + 1] / n
      out[fr * 3 + 2] += traj.lig[k + 2] / n
    }
  }
  return out
}
