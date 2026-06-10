export type Vec3 = [number, number, number]

// Small deterministic PRNG so the stylized cloud is stable across renders and sessions.
function mulberry32(seed: number) {
  return function () {
    seed |= 0
    seed = (seed + 0x6d2b79f5) | 0
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

export interface ResidueNode {
  pos: Vec3
  coreness: number // ~1 at the center, ~0 at the surface
}

const RADIUS = 4.2

// A deterministic globular cloud of `count` nodes. Illustrative geometry, NOT real coordinates.
export function residueNodes(count: number, seed = 5): ResidueNode[] {
  const rnd = mulberry32(seed)
  const nodes: ResidueNode[] = []
  for (let i = 0; i < count; i++) {
    const u = (i + 0.5) / count
    const phi = Math.acos(1 - 2 * u)
    const theta = Math.PI * (1 + Math.sqrt(5)) * i
    const rad = RADIUS * (0.6 + 0.4 * rnd())
    const pos: Vec3 = [
      rad * Math.sin(phi) * Math.cos(theta),
      rad * Math.cos(phi),
      rad * Math.sin(phi) * Math.sin(theta),
    ]
    nodes.push({ pos, coreness: 1 - rad / RADIUS })
  }
  return nodes
}

// Fixed pocket location and the unit direction the ligand approaches along.
export const POCKET: Vec3 = [2.6, 0.4, 2.2]
export const APPROACH_DIR: Vec3 = (() => {
  const v: Vec3 = [0.7, 0.25, 0.66]
  const m = Math.hypot(v[0], v[1], v[2])
  return [v[0] / m, v[1] / m, v[2] / m]
})()

// Ligand position at a given distance from the pocket, along the approach direction.
export function ligandPos(distance: number): Vec3 {
  const d = Math.min(distance, 32) // clamp the far end so it stays on screen
  return [
    POCKET[0] + APPROACH_DIR[0] * d,
    POCKET[1] + APPROACH_DIR[1] * d,
    POCKET[2] + APPROACH_DIR[2] * d,
  ]
}

// Indices (into the node array) of the k nodes closest to the pocket, used to light up contacts.
export function pocketNodeIndices(nodes: ResidueNode[], k: number): number[] {
  return nodes
    .map((n, i) => ({
      i,
      d: Math.hypot(n.pos[0] - POCKET[0], n.pos[1] - POCKET[1], n.pos[2] - POCKET[2]),
    }))
    .sort((a, b) => a.d - b.d)
    .slice(0, k)
    .map((x) => x.i)
}
