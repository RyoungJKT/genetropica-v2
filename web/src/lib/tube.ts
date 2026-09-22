// A tube through a chain of points (the protein's C-alpha trace), written into preallocated
// buffers so it can follow the trajectory every frame without allocating.
// Centreline: uniform Catmull-Rom through the points. Cross-section frame: parallel transport,
// so the tube does not twist. Radius: linear between the per-point radii.

export function tubeVertexCount(points: number, samples: number, radial: number): number {
  return ((points - 1) * samples + 1) * radial
}

export function tubeIndex(points: number, samples: number, radial: number): number[] {
  const rings = (points - 1) * samples + 1
  const idx: number[] = []
  for (let r = 0; r < rings - 1; r++) {
    for (let j = 0; j < radial; j++) {
      const a = r * radial + j
      const b = r * radial + ((j + 1) % radial)
      const c = a + radial
      const d = b + radial
      idx.push(a, c, b, b, c, d)
    }
  }
  return idx
}

function catmull(p0: number, p1: number, p2: number, p3: number, t: number): number {
  const t2 = t * t
  const t3 = t2 * t
  return 0.5 * (2 * p1 + (p2 - p0) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (3 * p1 - p0 - 3 * p2 + p3) * t3)
}

// Scratch space for the centreline, grown on demand and reused across calls.
let line = new Float32Array(0)

// Points are read from `src` starting at point `first` for `count` points (xyz packed);
// `radii` is indexed the same way, so both can be whole-protein arrays.
export function writeTube(
  src: Float32Array, first: number, count: number, radii: Float32Array,
  samples: number, radial: number, outPos: Float32Array, outNor: Float32Array,
): void {
  const rings = (count - 1) * samples + 1
  if (line.length < rings * 3) line = new Float32Array(rings * 3)
  const P = (i: number, axis: number) => src[(first + Math.max(0, Math.min(count - 1, i))) * 3 + axis]

  for (let s = 0; s < count - 1; s++) {
    for (let k = 0; k < samples; k++) {
      const t = k / samples
      const o = (s * samples + k) * 3
      for (let ax = 0; ax < 3; ax++) line[o + ax] = catmull(P(s - 1, ax), P(s, ax), P(s + 1, ax), P(s + 2, ax), t)
    }
  }
  for (let ax = 0; ax < 3; ax++) line[(rings - 1) * 3 + ax] = P(count - 1, ax)

  // Parallel-transported normal: start perpendicular to the first tangent, then at each ring
  // remove the component along the new tangent.
  let nx = 0, ny = 0, nz = 0
  for (let r = 0; r < rings; r++) {
    const a = Math.max(0, r - 1) * 3
    const b = Math.min(rings - 1, r + 1) * 3
    let tx = line[b] - line[a], ty = line[b + 1] - line[a + 1], tz = line[b + 2] - line[a + 2]
    const tl = Math.hypot(tx, ty, tz) || 1
    tx /= tl; ty /= tl; tz /= tl
    if (r === 0) {
      // any vector not parallel to the tangent
      if (Math.abs(tx) < 0.9) { nx = 1; ny = 0; nz = 0 } else { nx = 0; ny = 1; nz = 0 }
    }
    const d = nx * tx + ny * ty + nz * tz
    nx -= d * tx; ny -= d * ty; nz -= d * tz
    const nl = Math.hypot(nx, ny, nz) || 1
    nx /= nl; ny /= nl; nz /= nl
    const bx = ty * nz - tz * ny, by = tz * nx - tx * nz, bz = tx * ny - ty * nx

    const seg = Math.min(count - 2, Math.floor(r / samples))
    const f = r / samples - seg
    const rad = radii[first + seg] + (radii[first + seg + 1] - radii[first + seg]) * f
    for (let j = 0; j < radial; j++) {
      const th = (j / radial) * Math.PI * 2
      const c = Math.cos(th), sn = Math.sin(th)
      const ux = c * nx + sn * bx, uy = c * ny + sn * by, uz = c * nz + sn * bz
      const v = (r * radial + j) * 3
      outNor[v] = ux; outNor[v + 1] = uy; outNor[v + 2] = uz
      outPos[v] = line[r * 3] + rad * ux
      outPos[v + 1] = line[r * 3 + 1] + rad * uy
      outPos[v + 2] = line[r * 3 + 2] + rad * uz
    }
  }
}
