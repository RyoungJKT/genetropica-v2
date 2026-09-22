import { useEffect, useMemo, useRef } from 'react'
import type { MutableRefObject } from 'react'
import { Canvas, useFrame, useThree } from '@react-three/fiber'
import { OrbitControls } from '@react-three/drei'
import * as THREE from 'three'
import type { MdSeries } from '../../data/types'
import { chainSegments, frameSpan, lerpFrame, ligandCentroids, nearestFrame, trailSegments, type MdTraj } from '../../lib/mdTraj'
import { tubeIndex, tubeVertexCount, writeTube } from '../../lib/tube'

// Everything is in Angstrom, straight from the trajectory.
const SAMPLES = 4 // centreline samples per residue
const RADIAL = 8
const HELIX_R = 1.3
const STRAND_R = 1.05
const COIL_R = 0.45
const ATOM_R = 1.0
const BOND_R = 0.36
const MARKER_R = 1.6
const MAX_HB = 12
// Neutral slate so the three drug colours (green, clay, ochre) stand out against the protein.
const RIGID = new THREE.Color('#6d7b84')
const FLEXIBLE = new THREE.Color('#eef1f2')
const BOND_COLOR = new THREE.Color('#8a8a85')
const ELEMENT_COLOR: Record<string, string> = {
  C: '#4a4a48', N: '#2f5fb3', O: '#c23b22', S: '#d4a62a', F: '#5a9e6f', Cl: '#3f9a4f', Br: '#8b3a1a', P: '#d9822b',
}
const VIEW_DIR = new THREE.Vector3(0.35, 0.3, 1).normalize()
const UP = new THREE.Vector3(0, 1, 0)

// Shade each residue by its flexibility in this run: rigid dark, flexible pale.
function rmsfShades(series: MdSeries, n: number): THREE.Color[] {
  const vals = series.rmsf.map((p) => (p[1] ?? 0) as number)
  const sorted = [...vals].sort((a, b) => a - b)
  const lo = sorted[Math.floor(sorted.length * 0.05)] ?? 0
  const hi = sorted[Math.floor(sorted.length * 0.95)] ?? 1
  return Array.from({ length: n }, (_, i) => {
    const t = Math.max(0, Math.min(1, ((vals[i] ?? lo) - lo) / ((hi - lo) || 1)))
    return RIGID.clone().lerp(FLEXIBLE, t)
  })
}

// Bounding sphere of the protein plus the drug's whole path, so nothing leaves the frame.
function sceneSphere(traj: MdTraj): THREE.Sphere {
  const pts: THREE.Vector3[] = []
  for (let r = 0; r < traj.n_residues; r++) pts.push(new THREE.Vector3(traj.ca[r * 3], traj.ca[r * 3 + 1], traj.ca[r * 3 + 2]))
  for (let k = 0; k < traj.lig.length; k += 3) pts.push(new THREE.Vector3(traj.lig[k], traj.lig[k + 1], traj.lig[k + 2]))
  return new THREE.Sphere().setFromPoints(pts)
}

function FitCamera({ sphere }: { sphere: THREE.Sphere }) {
  // Read the camera through get() inside the effect: it is R3F's object to position, and the
  // react-hooks rules forbid mutating a value returned straight from a hook.
  const get = useThree((s) => s.get)
  const size = useThree((s) => s.size)
  useEffect(() => {
    const cam = get().camera as THREE.PerspectiveCamera
    const half = THREE.MathUtils.degToRad(cam.fov / 2)
    const fit = Math.min(Math.tan(half), Math.tan(half) * (size.width / size.height))
    const dist = (sphere.radius / fit) * 0.85
    cam.position.copy(sphere.center).addScaledVector(VIEW_DIR, dist)
    cam.near = Math.max(1, dist - sphere.radius * 1.5)
    cam.far = dist + sphere.radius * 3
    cam.up.copy(UP)
    cam.lookAt(sphere.center)
    cam.updateProjectionMatrix()
  }, [get, size.width, size.height, sphere])
  return null
}

function Trajectory({ traj, series, tNsRef, accent }: {
  traj: MdTraj
  series: MdSeries
  tNsRef: MutableRefObject<number>
  accent: string
}) {
  const nRes = traj.n_residues
  const nLig = traj.n_ligand_atoms
  const hot = useMemo(() => new THREE.Color(accent), [accent])
  const shades = useMemo(() => rmsfShades(series, nRes), [series, nRes])
  const radii = useMemo(
    () => Float32Array.from(traj.secondary_structure, (c) => (c === 'H' ? HELIX_R : c === 'E' ? STRAND_R : COIL_R)),
    [traj],
  )
  const centroids = useMemo(() => ligandCentroids(traj), [traj])
  const maxContacts = useMemo(() => Math.max(1, ...traj.contacts.map((c) => c.length)), [traj])
  const haloR = useMemo(() => {
    let r = 0
    for (let a = 0; a < nLig; a++) {
      r = Math.max(r, Math.hypot(traj.lig[a * 3] - centroids[0], traj.lig[a * 3 + 1] - centroids[1], traj.lig[a * 3 + 2] - centroids[2]))
    }
    return r + 2.5
  }, [traj, nLig, centroids])

  // One dynamic tube per chain fragment (5CCV chain A has breaks the model does not bridge).
  const tubes = useMemo(
    () =>
      chainSegments(traj)
        .filter(([a, b]) => b - a >= 2)
        .map(([first, end]) => {
          const count = end - first
          const vc = tubeVertexCount(count, SAMPLES, RADIAL)
          const geo = new THREE.BufferGeometry()
          for (const name of ['position', 'normal', 'color']) {
            geo.setAttribute(name, new THREE.BufferAttribute(new Float32Array(vc * 3), 3).setUsage(THREE.DynamicDrawUsage))
          }
          geo.setIndex(tubeIndex(count, SAMPLES, RADIAL))
          return { first, count, geo }
        }),
    [traj],
  )
  useEffect(() => () => tubes.forEach((t) => t.geo.dispose()), [tubes])

  // The drug's path so far: its centroid at every saved frame up to now, broken wherever it
  // switches to another periodic copy of the protein (a jump, not a movement).
  const trail = useMemo(() => {
    const segs = trailSegments(traj)
    const g = new THREE.BufferGeometry()
    g.setAttribute('position', new THREE.BufferAttribute(centroids, 3))
    g.setIndex(new THREE.BufferAttribute(segs, 1))
    g.setDrawRange(0, 0)
    // shownUpTo[i]: index count covering every segment that ends at or before frame i
    const shownUpTo = new Uint32Array(traj.frames)
    for (let k = 1; k < segs.length; k += 2) shownUpTo[segs[k]] = k + 1
    for (let i = 1; i < traj.frames; i++) shownUpTo[i] = Math.max(shownUpTo[i], shownUpTo[i - 1])
    const line = new THREE.LineSegments(g, new THREE.LineBasicMaterial({ color: accent, transparent: true, opacity: 0.45 }))
    line.frustumCulled = false
    return { line, shownUpTo }
  }, [traj, centroids, accent])
  const hbGeo = useMemo(() => {
    const g = new THREE.BufferGeometry()
    g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(MAX_HB * 6), 3).setUsage(THREE.DynamicDrawUsage))
    g.setDrawRange(0, 0)
    return g
  }, [])
  useEffect(() => () => { trail.line.geometry.dispose(); (trail.line.material as THREE.Material).dispose() }, [trail])
  useEffect(() => () => hbGeo.dispose(), [hbGeo])

  const atomsRef = useRef<THREE.InstancedMesh>(null)
  const bondsRef = useRef<THREE.InstancedMesh>(null)
  const markersRef = useRef<THREE.InstancedMesh>(null)
  const haloRef = useRef<THREE.Mesh>(null)
  const hbLineRef = useRef<THREE.LineSegments>(null)

  // Scratch buffers and bookkeeping live in a ref: mutated every frame, never read in render.
  const scratch = useRef({
    ca: new Float32Array(nRes * 3),
    lig: new Float32Array(nLig * 3),
    lastT: NaN,
    lastFrame: -1,
    obj: new THREE.Object3D(),
    a: new THREE.Vector3(),
    b: new THREE.Vector3(),
  })

  useEffect(() => {
    const atoms = atomsRef.current
    const bonds = bondsRef.current
    if (!atoms || !bonds) return
    traj.ligand_elements.forEach((el, i) => atoms.setColorAt(i, new THREE.Color(ELEMENT_COLOR[el] ?? '#9a6fb0')))
    for (let i = 0; i < traj.ligand_bonds.length; i++) bonds.setColorAt(i, BOND_COLOR)
    if (atoms.instanceColor) atoms.instanceColor.needsUpdate = true
    if (bonds.instanceColor) bonds.instanceColor.needsUpdate = true
  }, [traj])

  useFrame(() => {
    const s = scratch.current
    const tNs = tNsRef.current
    if (tNs === s.lastT) return
    s.lastT = tNs
    const span = frameSpan(traj, tNs)
    const frame = nearestFrame(traj, tNs)
    lerpFrame(traj.ca, nRes * 3, span, s.ca)
    lerpFrame(traj.lig, nLig * 3, span, s.lig)

    // Backbone follows the real C-alpha trace; contact residues take the drug's colour.
    const recolor = frame !== s.lastFrame
    const contactSet = new Set(traj.contacts[frame])
    for (const t of tubes) {
      const pos = t.geo.getAttribute('position') as THREE.BufferAttribute
      const nor = t.geo.getAttribute('normal') as THREE.BufferAttribute
      writeTube(s.ca, t.first, t.count, radii, SAMPLES, RADIAL, pos.array as Float32Array, nor.array as Float32Array)
      pos.needsUpdate = true
      nor.needsUpdate = true
      if (recolor) {
        const col = t.geo.getAttribute('color') as THREE.BufferAttribute
        const arr = col.array as Float32Array
        const rings = (t.count - 1) * SAMPLES + 1
        for (let r = 0; r < rings; r++) {
          const res = t.first + Math.min(t.count - 1, Math.round(r / SAMPLES))
          const c = contactSet.has(res) ? hot : shades[res]
          for (let j = 0; j < RADIAL; j++) {
            const v = (r * RADIAL + j) * 3
            arr[v] = c.r; arr[v + 1] = c.g; arr[v + 2] = c.b
          }
        }
        col.needsUpdate = true
      }
      if (!t.geo.boundingSphere) t.geo.computeBoundingSphere()
    }

    const markers = markersRef.current
    if (markers) {
      const list = traj.contacts[frame]
      list.forEach((res, i) => {
        s.obj.position.set(s.ca[res * 3], s.ca[res * 3 + 1], s.ca[res * 3 + 2])
        s.obj.quaternion.identity()
        s.obj.scale.setScalar(MARKER_R)
        s.obj.updateMatrix()
        markers.setMatrixAt(i, s.obj.matrix)
      })
      markers.count = list.length
      markers.instanceMatrix.needsUpdate = true
    }

    // Drug: every heavy atom where the simulation put it, bonds from the force-field topology.
    const atoms = atomsRef.current
    const bonds = bondsRef.current
    if (atoms && bonds) {
      for (let i = 0; i < nLig; i++) {
        s.obj.position.set(s.lig[i * 3], s.lig[i * 3 + 1], s.lig[i * 3 + 2])
        s.obj.quaternion.identity()
        s.obj.scale.setScalar(ATOM_R)
        s.obj.updateMatrix()
        atoms.setMatrixAt(i, s.obj.matrix)
      }
      traj.ligand_bonds.forEach(([i, j], k) => {
        s.a.set(s.lig[i * 3], s.lig[i * 3 + 1], s.lig[i * 3 + 2])
        s.b.set(s.lig[j * 3], s.lig[j * 3 + 1], s.lig[j * 3 + 2])
        const len = s.a.distanceTo(s.b)
        s.obj.position.copy(s.a).add(s.b).multiplyScalar(0.5)
        s.obj.quaternion.setFromUnitVectors(UP, s.b.sub(s.a).normalize())
        s.obj.scale.set(BOND_R, len, BOND_R)
        s.obj.updateMatrix()
        bonds.setMatrixAt(k, s.obj.matrix)
      })
      atoms.instanceMatrix.needsUpdate = true
      bonds.instanceMatrix.needsUpdate = true
    }

    let cx = 0, cy = 0, cz = 0
    for (let i = 0; i < nLig; i++) { cx += s.lig[i * 3] / nLig; cy += s.lig[i * 3 + 1] / nLig; cz += s.lig[i * 3 + 2] / nLig }
    haloRef.current?.position.set(cx, cy, cz)
    trail.line.geometry.setDrawRange(0, trail.shownUpTo[span.i0])

    // Hydrogen bonds at the nearest saved frame: drug atom to its protein partner atom.
    const hbs = traj.hbonds[frame].slice(0, MAX_HB)
    const hp = (hbGeo.getAttribute('position') as THREE.BufferAttribute)
    const harr = hp.array as Float32Array
    hbs.forEach(([atom, x, y, z], k) => {
      harr.set([s.lig[atom * 3], s.lig[atom * 3 + 1], s.lig[atom * 3 + 2], x, y, z], k * 6)
    })
    hp.needsUpdate = true
    hbGeo.setDrawRange(0, hbs.length * 2)
    hbLineRef.current?.computeLineDistances()
    s.lastFrame = frame
  })

  return (
    <group>
      {tubes.map((t) => (
        <mesh key={t.first} geometry={t.geo} frustumCulled={false}>
          <meshStandardMaterial vertexColors roughness={0.55} metalness={0.05} />
        </mesh>
      ))}
      <instancedMesh ref={markersRef} args={[undefined, undefined, maxContacts]} frustumCulled={false}>
        <sphereGeometry args={[1, 12, 12]} />
        <meshStandardMaterial color={accent} roughness={0.4} transparent opacity={0.8} depthWrite={false} />
      </instancedMesh>
      <instancedMesh ref={atomsRef} args={[undefined, undefined, nLig]} frustumCulled={false}>
        <sphereGeometry args={[1, 16, 16]} />
        <meshStandardMaterial roughness={0.35} metalness={0.05} />
      </instancedMesh>
      <instancedMesh ref={bondsRef} args={[undefined, undefined, Math.max(1, traj.ligand_bonds.length)]} frustumCulled={false}>
        <cylinderGeometry args={[1, 1, 1, 10]} />
        <meshStandardMaterial roughness={0.5} />
      </instancedMesh>
      <mesh ref={haloRef} frustumCulled={false}>
        <sphereGeometry args={[haloR, 24, 24]} />
        <meshBasicMaterial color={accent} transparent opacity={0.16} depthWrite={false} />
      </mesh>
      <primitive object={trail.line} />
      <lineSegments ref={hbLineRef} geometry={hbGeo} frustumCulled={false}>
        <lineDashedMaterial color="#2f5fb3" dashSize={0.6} gapSize={0.4} />
      </lineSegments>
    </group>
  )
}

export function MdScene({ traj, series, tNsRef, accent }: {
  traj: MdTraj
  series: MdSeries
  tNsRef: MutableRefObject<number>
  accent: string
}) {
  const sphere = useMemo(() => sceneSphere(traj), [traj])
  const center = useMemo(() => sphere.center.toArray(), [sphere])
  return (
    <Canvas key={traj.drug} camera={{ fov: 38 }} dpr={[1, 2]} style={{ height: '100%', width: '100%' }}>
      <ambientLight intensity={1.05} />
      <directionalLight position={[60, 90, 70]} intensity={1.05} />
      <directionalLight position={[-70, -30, -50]} intensity={0.35} />
      <FitCamera sphere={sphere} />
      <Trajectory traj={traj} series={series} tNsRef={tNsRef} accent={accent} />
      <OrbitControls target={center} enablePan={false} enableDamping minDistance={15} maxDistance={sphere.radius * 5} />
    </Canvas>
  )
}
