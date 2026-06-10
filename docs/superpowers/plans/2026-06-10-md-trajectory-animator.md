# MD Trajectory Animator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a data-driven react-three-fiber hero animation to the top of the MD page that lets a viewer watch each candidate drug associate (or fail) with NS5 over the real 50 ns trajectory.

**Architecture:** Pure mapping functions read the existing `md.json` series (approach from `mindist`, shimmer from `rmsf`, contacts/H-bonds from their series). A stylized R3F scene (one instanced-mesh residue cloud plus a ligand) reads the current time through a ref each frame. A container owns the drug selector, play/scrub clock, readout and honesty caption, and emits the current time so the existing charts can show a synced playhead.

**Tech Stack:** React 18, TypeScript, Vite, react-three-fiber + three + drei (already installed), vitest (added in Task 1 for the pure-function tests).

**Working directory for all commands:** `/Users/darwin/Developer/genetropica-v2/web`

**Spec:** `docs/superpowers/specs/2026-06-10-md-trajectory-animator-design.md`

**Conventions for every commit in this plan:**
```bash
git -c user.name='RyoungJKT' -c user.email='RyoungJKT@users.noreply.github.com' commit -m "<message>"
```
No `Co-Authored-By` trailer. No em dashes in messages (use commas/periods). Do not stage `.claude/launch.json`.

---

### Task 1: Add the vitest test runner

**Files:**
- Modify: `package.json` (add devDependency + `test` script)
- Modify: `vite.config.ts`
- Create: `src/lib/smoke.test.ts` (temporary, deleted at end of task)

- [ ] **Step 1: Install vitest**

Run: `npm i -D vitest`
Expected: `vitest` appears under `devDependencies` in `package.json`.

- [ ] **Step 2: Add the test script**

In `package.json`, add to `"scripts"`:
```json
"test": "vitest run"
```

- [ ] **Step 3: Add a node-env test block to vite config**

Replace the contents of `vite.config.ts` with:
```ts
/// <reference types="vitest/config" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  // The dashboard is mounted under /app; the static landing page is served at the site root.
  base: '/app/',
  plugins: [react()],
  build: { outDir: 'dist/app' },
  test: { environment: 'node', include: ['src/**/*.test.ts'] },
})
```

- [ ] **Step 4: Write a smoke test**

Create `src/lib/smoke.test.ts`:
```ts
import { describe, it, expect } from 'vitest'

describe('vitest', () => {
  it('runs', () => {
    expect(1 + 1).toBe(2)
  })
})
```

- [ ] **Step 5: Run the test and the build**

Run: `npm run test`
Expected: 1 passed.

Run: `npm run build`
Expected: build completes (exit 0). If `tsc -b` errors because the test file is outside the app tsconfig include, add `"src/**/*.test.ts"` is already covered by `src`; if a separate `tsconfig.app.json` excludes tests, add `"**/*.test.ts"` to its `exclude` so the production typecheck skips test files. Re-run until both `npm run test` and `npm run build` pass.

- [ ] **Step 6: Delete the smoke test and commit**

Run: `rm src/lib/smoke.test.ts`
```bash
git add package.json package-lock.json vite.config.ts
git -c user.name='RyoungJKT' -c user.email='RyoungJKT@users.noreply.github.com' commit -m "test: add vitest runner for pure-function unit tests"
```

---

### Task 2: Pure motion-mapping functions

**Files:**
- Create: `src/lib/mdMotion.ts`
- Test: `src/lib/mdMotion.test.ts`

These functions are the honesty-critical core: they map the real `md.json` series to the numbers the scene renders. `MdSeries` (from `src/data/types.ts`) is:
```ts
export interface MdSeries {
  rmsd: (number | null)[][]      // points [t_ns, protein_rmsd, ligand_rmsd]
  hbonds: (number | null)[][]    // points [t_ns, n]
  mindist: (number | null)[][]   // points [t_ns, distance_A]
  rmsf: (number | null)[][]      // points [residue_index, rmsf_A]
  ncontacts: (number | null)[][] // points [t_ns, n]
  contacts: number[][]           // [resid, occupancy_pct]
}
```

- [ ] **Step 1: Write the failing tests**

Create `src/lib/mdMotion.test.ts`:
```ts
import { readFileSync } from 'node:fs'
import { describe, it, expect } from 'vitest'
import type { Md } from '../data/types'
import { distanceAt, ligandRmsdAt, proteinRmsdAt, hbondsAt, ncontactsAt, rmsfFor, residueCount, frameReadout, DURATION_NS } from './mdMotion'

const md: Md = JSON.parse(readFileSync(new URL('../../public/data/md.json', import.meta.url), 'utf8'))
const cele = md.series.celecoxib
const metho = md.series.methotrexate
const dasa = md.series.dasabuvir

describe('distanceAt (real trajectory)', () => {
  it('celecoxib starts far and associates fast', () => {
    expect(distanceAt(cele, 0)).toBeGreaterThan(18)
    expect(distanceAt(cele, 5)).toBeLessThan(3)
    expect(distanceAt(cele, 50)).toBeLessThan(5)
  })
  it('methotrexate is still far at 5 ns and associated by 25 ns', () => {
    expect(distanceAt(metho, 5)).toBeGreaterThan(10)
    expect(distanceAt(metho, 25)).toBeLessThan(3)
  })
  it('dasabuvir never settles', () => {
    expect(distanceAt(dasa, 25)).toBeGreaterThan(10)
    expect(distanceAt(dasa, 50)).toBeGreaterThan(5)
  })
})

describe('ligandRmsdAt', () => {
  it('is null for dasabuvir (no stable pose, zero ligand-RMSD points)', () => {
    expect(ligandRmsdAt(dasa, 25)).toBeNull()
  })
  it('is a number for celecoxib once associated', () => {
    expect(typeof ligandRmsdAt(cele, 25)).toBe('number')
  })
})

describe('counts and per-residue', () => {
  it('hbonds and ncontacts are non-negative integers in range', () => {
    expect(Number.isInteger(hbondsAt(cele, 25))).toBe(true)
    expect(hbondsAt(cele, 25)).toBeGreaterThanOrEqual(0)
    expect(ncontactsAt(cele, 25)).toBeGreaterThanOrEqual(0)
  })
  it('proteinRmsdAt is a finite positive number', () => {
    expect(proteinRmsdAt(cele, 25)).toBeGreaterThan(0)
  })
  it('residueCount is 849 and rmsfFor returns a positive value', () => {
    expect(residueCount(cele)).toBe(849)
    expect(rmsfFor(cele, 0)).toBeGreaterThan(0)
    expect(rmsfFor(cele, 10_000)).toBeGreaterThan(0) // clamps out-of-range index
  })
})

describe('frameReadout and constants', () => {
  it('returns the live readout fields and DURATION_NS is 50', () => {
    const r = frameReadout(cele, 12.5)
    expect(r.tNs).toBe(12.5)
    expect(r.distance).toBeGreaterThan(0)
    expect(DURATION_NS).toBe(50)
  })
})
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `npm run test`
Expected: FAIL, `mdMotion.ts` does not exist / functions undefined.

- [ ] **Step 3: Implement the mapping functions**

Create `src/lib/mdMotion.ts`:
```ts
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
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `npm run test`
Expected: all `mdMotion` tests pass.

- [ ] **Step 5: Commit**
```bash
git add src/lib/mdMotion.ts src/lib/mdMotion.test.ts
git -c user.name='RyoungJKT' -c user.email='RyoungJKT@users.noreply.github.com' commit -m "feat(md): pure motion-mapping functions from the real MD series"
```

---

### Task 3: Stylized layout geometry

**Files:**
- Create: `src/lib/mdLayout.ts`
- Test: `src/lib/mdLayout.test.ts`

- [ ] **Step 1: Write the failing tests**

Create `src/lib/mdLayout.test.ts`:
```ts
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
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `npm run test`
Expected: FAIL, `mdLayout.ts` does not exist.

- [ ] **Step 3: Implement the layout**

Create `src/lib/mdLayout.ts`:
```ts
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
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `npm run test`
Expected: all `mdLayout` tests pass.

- [ ] **Step 5: Commit**
```bash
git add src/lib/mdLayout.ts src/lib/mdLayout.test.ts
git -c user.name='RyoungJKT' -c user.email='RyoungJKT@users.noreply.github.com' commit -m "feat(md): deterministic stylized layout for the animator scene"
```

---

### Task 4: Add a synced playhead to MultiLineChart

**Files:**
- Modify: `src/components/MultiLineChart.tsx`

The chart already builds an x scale named `x`. Add an optional `playheadX` data-space value and draw a vertical guide at it. Backward compatible: existing call sites pass nothing and render unchanged.

- [ ] **Step 1: Add the prop to the signature**

In `src/components/MultiLineChart.tsx`, change the function signature line:
```tsx
export function MultiLineChart({ lines, xLabel, yLabel, yMin }: { lines: ChartLine[]; xLabel: string; yLabel: string; yMin?: number }) {
```
to:
```tsx
export function MultiLineChart({ lines, xLabel, yLabel, yMin, playheadX }: { lines: ChartLine[]; xLabel: string; yLabel: string; yMin?: number; playheadX?: number }) {
```

- [ ] **Step 2: Draw the playhead line**

In the same file, find the lines-drawing block (the `{lines.map((l, li) => ...)}` expression inside `<g transform=...>`). Immediately AFTER that `{lines.map(...)}` expression and BEFORE the `{hoverItems && ...}` block, insert:
```tsx
{playheadX != null && (
  <line
    x1={x(playheadX)}
    y1={0}
    x2={x(playheadX)}
    y2={IH}
    stroke="var(--ink)"
    strokeWidth={1}
    opacity={0.45}
  />
)}
```

- [ ] **Step 3: Typecheck**

Run: `npx tsc -b`
Expected: exit 0, no errors.

- [ ] **Step 4: Commit**
```bash
git add src/components/MultiLineChart.tsx
git -c user.name='RyoungJKT' -c user.email='RyoungJKT@users.noreply.github.com' commit -m "feat(chart): optional synced playhead line on MultiLineChart"
```

---

### Task 5: The R3F scene

**Files:**
- Create: `src/components/md/MdScene.tsx`

The scene reads the current time through a ref (`tNsRef`) so scrub/play updates do not re-mount the canvas. Residues are one instanced mesh; the ligand is a small cluster; H-bonds are thin lines drawn to pocket nodes when associated.

- [ ] **Step 1: Implement the scene**

Create `src/components/md/MdScene.tsx`:
```tsx
import { useMemo, useRef } from 'react'
import type { MutableRefObject } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import * as THREE from 'three'
import type { MdSeries } from '../../data/types'
import { distanceAt, hbondsAt, ncontactsAt, rmsfFor, residueCount } from '../../lib/mdMotion'
import { residueNodes, ligandPos, pocketNodeIndices, type ResidueNode } from '../../lib/mdLayout'

const MAX_NODES_MOBILE = 320
const ASSOC_DIST = 6 // A, below this the drug counts as at the pocket
const MAX_HB = 8

function Protein({ series, tNsRef, accent, nodes, pocketIdx }: {
  series: MdSeries
  tNsRef: MutableRefObject<number>
  accent: string
  nodes: ResidueNode[]
  pocketIdx: Set<number>
}) {
  const meshRef = useRef<THREE.InstancedMesh>(null)
  const dummy = useMemo(() => new THREE.Object3D(), [])
  const surface = useMemo(() => new THREE.Color('#9fb3aa'), [])
  const core = useMemo(() => new THREE.Color('#1f5740'), [])
  const hot = useMemo(() => new THREE.Color(accent), [accent])

  useFrame((state) => {
    const mesh = meshRef.current
    if (!mesh) return
    const tNs = tNsRef.current
    const time = state.clock.elapsedTime
    const associated = distanceAt(series, tNs) < ASSOC_DIST
    let litLeft = associated ? Math.min(pocketIdx.size, ncontactsAt(series, tNs)) : 0
    for (let i = 0; i < nodes.length; i++) {
      const n = nodes[i]
      const amp = 0.06 + 0.05 * rmsfFor(series, i)
      const jitter = Math.sin(time * 1.6 + i * 1.7) * amp
      dummy.position.set(n.pos[0], n.pos[1] + jitter, n.pos[2])
      dummy.scale.setScalar(0.16)
      dummy.updateMatrix()
      mesh.setMatrixAt(i, dummy.matrix)
      const isLit = pocketIdx.has(i) && litLeft > 0
      if (isLit) litLeft--
      const color = isLit ? hot : surface.clone().lerp(core, n.coreness)
      mesh.setColorAt(i, color)
    }
    mesh.instanceMatrix.needsUpdate = true
    if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true
  })

  return (
    <instancedMesh ref={meshRef} args={[undefined, undefined, nodes.length]} frustumCulled={false}>
      <sphereGeometry args={[1, 8, 8]} />
      <meshStandardMaterial roughness={0.6} metalness={0.05} />
    </instancedMesh>
  )
}

function Ligand({ series, tNsRef, accent }: {
  series: MdSeries
  tNsRef: MutableRefObject<number>
  accent: string
}) {
  const groupRef = useRef<THREE.Group>(null)
  const offsets: [number, number, number][] = useMemo(
    () => [
      [0, 0, 0],
      [0.28, 0.1, 0],
      [-0.16, 0.22, 0.1],
      [0.1, -0.2, -0.16],
    ],
    [],
  )
  useFrame((state) => {
    const g = groupRef.current
    if (!g) return
    const p = ligandPos(distanceAt(series, tNsRef.current))
    const wob = 0.04 * Math.sin(state.clock.elapsedTime * 3)
    g.position.set(p[0] + wob, p[1] - wob, p[2])
  })
  return (
    <group ref={groupRef}>
      {offsets.map((o, i) => (
        <mesh key={i} position={o}>
          <sphereGeometry args={[0.22, 12, 12]} />
          <meshStandardMaterial color={accent} roughness={0.35} metalness={0.1} emissive={accent} emissiveIntensity={0.15} />
        </mesh>
      ))}
    </group>
  )
}

function HBonds({ series, tNsRef, nodes, pocketIdx }: {
  series: MdSeries
  tNsRef: MutableRefObject<number>
  nodes: ResidueNode[]
  pocketIdx: Set<number>
}) {
  const ref = useRef<THREE.LineSegments>(null)
  const positions = useMemo(() => new Float32Array(MAX_HB * 2 * 3), [])
  const pocketArr = useMemo(() => [...pocketIdx], [pocketIdx])
  useFrame(() => {
    const ls = ref.current
    if (!ls || pocketArr.length === 0) return
    const tNs = tNsRef.current
    const dist = distanceAt(series, tNs)
    const lp = ligandPos(dist)
    const n = dist < ASSOC_DIST ? Math.min(MAX_HB, hbondsAt(series, tNs)) : 0
    for (let i = 0; i < n; i++) {
      const node = nodes[pocketArr[i % pocketArr.length]]
      positions[i * 6 + 0] = lp[0]
      positions[i * 6 + 1] = lp[1]
      positions[i * 6 + 2] = lp[2]
      positions[i * 6 + 3] = node.pos[0]
      positions[i * 6 + 4] = node.pos[1]
      positions[i * 6 + 5] = node.pos[2]
    }
    const geom = ls.geometry as THREE.BufferGeometry
    geom.setDrawRange(0, n * 2)
    ;(geom.attributes.position as THREE.BufferAttribute).needsUpdate = true
  })
  return (
    <lineSegments ref={ref}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" array={positions} count={MAX_HB * 2} itemSize={3} />
      </bufferGeometry>
      <lineBasicMaterial color="#6b8a7d" transparent opacity={0.7} />
    </lineSegments>
  )
}

export function MdScene({ series, tNsRef, accent, reducedNodes }: {
  series: MdSeries
  tNsRef: MutableRefObject<number>
  accent: string
  reducedNodes: boolean
}) {
  const total = residueCount(series)
  const count = reducedNodes ? Math.min(total, MAX_NODES_MOBILE) : total
  const nodes = useMemo(() => residueNodes(count), [count])
  const pocketIdx = useMemo(() => new Set(pocketNodeIndices(nodes, 14)), [nodes])
  return (
    <Canvas camera={{ position: [0, 6, 11], fov: 42 }} dpr={[1, 2]} style={{ height: '100%', width: '100%' }}>
      <ambientLight intensity={0.78} />
      <directionalLight position={[5, 8, 6]} intensity={1.0} />
      <directionalLight position={[-6, -2, -4]} intensity={0.36} />
      <Protein series={series} tNsRef={tNsRef} accent={accent} nodes={nodes} pocketIdx={pocketIdx} />
      <HBonds series={series} tNsRef={tNsRef} nodes={nodes} pocketIdx={pocketIdx} />
      <Ligand series={series} tNsRef={tNsRef} accent={accent} />
    </Canvas>
  )
}
```

- [ ] **Step 2: Typecheck**

Run: `npx tsc -b`
Expected: exit 0. If three's `bufferAttribute`/`instancedMesh` JSX intrinsics report type errors, confirm `@react-three/fiber` is imported in the file (its module augmentation registers the intrinsics); no other change should be needed.

- [ ] **Step 3: Commit**
```bash
git add src/components/md/MdScene.tsx
git -c user.name='RyoungJKT' -c user.email='RyoungJKT@users.noreply.github.com' commit -m "feat(md): R3F scene driven by the real trajectory through a time ref"
```

---

### Task 6: The animator container

**Files:**
- Create: `src/components/md/MdAnimator.tsx`

Owns the drug selector, the play/scrub clock, the live readout and the honesty caption. Advances `tNs` with `requestAnimationFrame`, keeps `tNsRef` in sync for the scene, and emits a throttled time via `onTime` for the page's chart playhead. Honors reduced motion.

- [ ] **Step 1: Implement the container**

Create `src/components/md/MdAnimator.tsx`:
```tsx
import { useEffect, useRef, useState } from 'react'
import { useMd } from '../../data/api'
import { MdScene } from './MdScene'
import { frameReadout, DURATION_NS } from '../../lib/mdMotion'

const DRUGS = ['celecoxib', 'methotrexate', 'dasabuvir'] as const
type Drug = (typeof DRUGS)[number]
const LABEL: Record<Drug, string> = { celecoxib: 'Celecoxib', methotrexate: 'Methotrexate', dasabuvir: 'Dasabuvir' }
const ACCENT: Record<Drug, string> = { celecoxib: '#1F5740', methotrexate: '#A8492B', dasabuvir: '#A8742C' }
const SPEED_NS_PER_SEC = 12 // about 4 s for a full 50 ns pass

function prefersReducedMotion(): boolean {
  return typeof window !== 'undefined' && !!window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
}

export function MdAnimator({ onTime }: { onTime?: (tNs: number) => void }) {
  const md = useMd()
  const reduced = prefersReducedMotion()
  const isMobile = typeof window !== 'undefined' && window.innerWidth < 760
  const [drug, setDrug] = useState<Drug>('celecoxib')
  const [playing, setPlaying] = useState(!reduced)
  const [tNs, setTNs] = useState(reduced ? DURATION_NS * 0.5 : 0)
  const tNsRef = useRef(tNs)
  const rafRef = useRef(0)
  const lastTs = useRef(0)
  const lastEmit = useRef(-1)

  // keep the ref in sync for the scene, and emit a throttled time for the chart playhead
  useEffect(() => {
    tNsRef.current = tNs
    if (onTime && Math.abs(tNs - lastEmit.current) >= 0.5) {
      lastEmit.current = tNs
      onTime(tNs)
    }
  }, [tNs, onTime])

  useEffect(() => {
    if (!playing) return
    lastTs.current = 0
    const step = (ts: number) => {
      if (!lastTs.current) lastTs.current = ts
      const dt = (ts - lastTs.current) / 1000
      lastTs.current = ts
      setTNs((prev) => {
        const next = prev + dt * SPEED_NS_PER_SEC
        return next >= DURATION_NS ? 0 : next
      })
      rafRef.current = requestAnimationFrame(step)
    }
    rafRef.current = requestAnimationFrame(step)
    return () => cancelAnimationFrame(rafRef.current)
  }, [playing])

  const series = md.data?.series[drug]
  if (!md.data || !series) {
    return (
      <div className="mono" style={{ height: 360, display: 'grid', placeItems: 'center', color: 'var(--ink-faint)' }}>
        Loading simulation...
      </div>
    )
  }
  const readout = frameReadout(series, tNs)

  return (
    <div style={{ marginTop: 18, border: '1px solid var(--line)', borderRadius: 16, overflow: 'hidden', background: 'var(--paper)' }}>
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', padding: '12px 14px', borderBottom: '1px solid var(--line)' }}>
        {DRUGS.map((d) => (
          <button
            key={d}
            onClick={() => setDrug(d)}
            style={{
              fontFamily: 'var(--mono)', fontSize: 11, letterSpacing: '.04em', textTransform: 'uppercase',
              padding: '6px 12px', borderRadius: 999, cursor: 'pointer',
              border: `1px solid ${drug === d ? ACCENT[d] : 'var(--line)'}`,
              background: drug === d ? ACCENT[d] : 'transparent',
              color: drug === d ? '#fff' : 'var(--ink-soft)',
            }}
          >
            {LABEL[d]}
          </button>
        ))}
      </div>

      <div style={{ position: 'relative', height: isMobile ? 300 : 420, background: 'radial-gradient(circle at 50% 38%, var(--paper-2), var(--paper))' }}>
        <MdScene series={series} tNsRef={tNsRef} accent={ACCENT[drug]} reducedNodes={isMobile} />
        <div style={{ position: 'absolute', left: 14, bottom: 12, fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--ink-soft)', lineHeight: 1.5, background: 'color-mix(in srgb, var(--paper) 72%, transparent)', borderRadius: 8, padding: '6px 10px' }}>
          <div>t = {readout.tNs.toFixed(1)} ns</div>
          <div>min dist = {Number.isFinite(readout.distance) ? `${readout.distance.toFixed(1)} A` : '-'}</div>
          <div>H-bonds = {readout.hbonds} &nbsp; contacts = {readout.ncontacts}</div>
        </div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '12px 14px', borderTop: '1px solid var(--line)' }}>
        <button
          onClick={() => setPlaying((p) => !p)}
          style={{ fontFamily: 'var(--mono)', fontSize: 12, padding: '6px 14px', borderRadius: 8, border: '1px solid var(--line)', background: 'var(--paper-2)', cursor: 'pointer', color: 'var(--ink)' }}
        >
          {playing ? 'Pause' : 'Play'}
        </button>
        <input
          type="range" min={0} max={DURATION_NS} step={0.25} value={tNs}
          onChange={(e) => { setPlaying(false); setTNs(parseFloat(e.target.value)) }}
          aria-label="Scrub simulation time"
          style={{ flex: 1, accentColor: ACCENT[drug] }}
        />
        <span style={{ fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--ink-faint)', minWidth: 70, textAlign: 'right' }}>
          {tNs.toFixed(1)} / {DURATION_NS} ns
        </span>
      </div>

      <p style={{ fontSize: 12, color: 'var(--ink-faint)', lineHeight: 1.55, margin: 0, padding: '0 14px 14px' }}>
        Stylized view. The approach distance and timing, per-residue flexibility, H-bonds and contacts are taken frame-by-frame from the real 50 ns simulation. The protein's shape and the drug's exact 3D path are illustrative; the full atomic trajectory was not stored. Schematic, not to scale.
      </p>
    </div>
  )
}
```

- [ ] **Step 2: Typecheck**

Run: `npx tsc -b`
Expected: exit 0.

- [ ] **Step 3: Commit**
```bash
git add src/components/md/MdAnimator.tsx
git -c user.name='RyoungJKT' -c user.email='RyoungJKT@users.noreply.github.com' commit -m "feat(md): animator container with selector, scrub clock, readout, caption"
```

---

### Task 7: Wire the animator into the MD page

**Files:**
- Modify: `src/pages/MD.tsx`

Mount the animator as a hero under the association callout, hold the playhead time in page state, and pass `playheadX` to the time-axis charts (protein RMSD, ligand RMSD, min-distance, H-bonds, contacts). Do NOT pass it to the RMSF chart, whose x axis is residue, not time.

- [ ] **Step 1: Add imports**

In `src/pages/MD.tsx`, add `useState` to the React import and import the animator. At the top, the existing first import is:
```tsx
import type { ReactNode, CSSProperties } from 'react'
```
Add directly below it:
```tsx
import { useState } from 'react'
import { MdAnimator } from '../components/md/MdAnimator'
```

- [ ] **Step 2: Add playhead state**

In the `MD()` component body, find:
```tsx
  const md = useMd()
  const { reg } = useRegister()
```
and add below it:
```tsx
  const [playheadNs, setPlayheadNs] = useState(0)
```

- [ ] **Step 3: Mount the animator under the callout**

Find this block:
```tsx
      <div style={{ background: 'var(--paper-2)', border: '1px solid var(--line)', borderRadius: 12, padding: '14px 18px', margin: '18px 0 8px', fontSize: 14, color: 'var(--ink-soft)', lineHeight: 1.6, maxWidth: 760 }}>
        Celecoxib associates at about 3 ns and stays; methotrexate associates at about 14 ns and remains mobile; dasabuvir never forms a stable bound pose within 50 ns.
      </div>
```
Insert directly AFTER it (mount unconditionally; the animator renders its own loading state):
```tsx
      <MdAnimator onTime={setPlayheadNs} />
```

- [ ] **Step 4: Pass the playhead to the time-axis charts**

In the same file, add `playheadX={playheadNs}` to the five time-axis charts. Make these exact replacements:

```tsx
            <MultiLineChart lines={series('rmsd', 1)} xLabel="time (ns)" yLabel="RMSD (Å)" yMin={0} />
```
to
```tsx
            <MultiLineChart lines={series('rmsd', 1)} xLabel="time (ns)" yLabel="RMSD (Å)" yMin={0} playheadX={playheadNs} />
```

```tsx
            <MultiLineChart lines={series('rmsd', 2)} xLabel="time (ns)" yLabel="RMSD (Å)" yMin={0} />
```
to
```tsx
            <MultiLineChart lines={series('rmsd', 2)} xLabel="time (ns)" yLabel="RMSD (Å)" yMin={0} playheadX={playheadNs} />
```

```tsx
            <MultiLineChart lines={series('mindist', 1)} xLabel="time (ns)" yLabel="min distance (Å)" yMin={0} />
```
to
```tsx
            <MultiLineChart lines={series('mindist', 1)} xLabel="time (ns)" yLabel="min distance (Å)" yMin={0} playheadX={playheadNs} />
```

```tsx
            <MultiLineChart lines={series('hbonds', 1)} xLabel="time (ns)" yLabel="H-bonds" yMin={0} />
```
to
```tsx
            <MultiLineChart lines={series('hbonds', 1)} xLabel="time (ns)" yLabel="H-bonds" yMin={0} playheadX={playheadNs} />
```

```tsx
            <MultiLineChart lines={series('ncontacts', 1)} xLabel="time (ns)" yLabel="contacts (< 4.5 Å)" yMin={0} />
```
to
```tsx
            <MultiLineChart lines={series('ncontacts', 1)} xLabel="time (ns)" yLabel="contacts (< 4.5 Å)" yMin={0} playheadX={playheadNs} />
```

Leave the RMSF chart (`series('rmsf', 1)`, xLabel "residue") unchanged: it has no time axis.

- [ ] **Step 5: Typecheck and build**

Run: `npx tsc -b`
Expected: exit 0.

Run: `npm run build`
Expected: build completes (exit 0).

- [ ] **Step 6: Commit**
```bash
git add src/pages/MD.tsx
git -c user.name='RyoungJKT' -c user.email='RyoungJKT@users.noreply.github.com' commit -m "feat(md): mount the trajectory animator and sync chart playheads"
```

---

### Task 8: Final verification

**Files:** none (verification only)

- [ ] **Step 1: Full test + build gate**

Run: `npm run test`
Expected: all `mdMotion` and `mdLayout` tests pass.

Run: `npm run build`
Expected: exit 0, `dist/app/` written.

- [ ] **Step 2: Lint**

Run: `npm run lint`
Expected: no new errors in the added files. Fix any reported in `src/lib/mdMotion.ts`, `src/lib/mdLayout.ts`, `src/components/md/MdScene.tsx`, `src/components/md/MdAnimator.tsx`, `src/pages/MD.tsx`.

- [ ] **Step 3: Push**

```bash
git push origin main
```

- [ ] **Step 4: Deploy review**

The preview sandbox cannot reach this repo, so confirm visually on the live Vercel deploy: open the MD page (`/app/md`), check that the hero animator loads, the three drug pills switch runs, Play and the scrub slider move the drug in and out (celecoxib locks early, dasabuvir stays out), and the playhead line tracks across the time charts below. Note anything off for a follow-up pass.

---

## Notes for the implementer

- All motion must trace to a value in `md.json`. Do not introduce randomized "wiggle" beyond the RMSF-scaled shimmer and the small fixed wobble already specified; the honesty caption depends on this being true.
- Lit contacts: the *number* of lit nodes tracks the real `ncontacts` count, but the specific lit nodes are the pocket-nearest ones (for visual coherence), not mapped to the literal `contacts` residue numbers. This is honest because the caption claims the count, not identities; the actual named contact residues are already listed in the page's existing "Top contact residues" section. Do not relabel the lit nodes with residue numbers.
- `--paper`, `--paper-2`, `--ink`, `--ink-soft`, `--ink-faint`, `--line`, `--mono` are existing CSS tokens used elsewhere in the page; reuse them, do not hard-code new colors except the per-drug accents already defined.
- If `npm run build`'s `tsc -b` pulls test files into the production typecheck and that causes friction, exclude `**/*.test.ts` in the app tsconfig's `exclude`; keep `vitest`'s `include` pointing at `src/**/*.test.ts`.
