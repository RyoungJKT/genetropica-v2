import { useEffect, useMemo, useRef } from 'react'
import type { MutableRefObject } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import * as THREE from 'three'
import type { MdSeries } from '../../data/types'
import { distanceAt, hbondsAt, ncontactsAt, rmsfFor, residueCount } from '../../lib/mdMotion'
import { residueNodes, ligandPos, pocketNodeIndices, type ResidueNode } from '../../lib/mdLayout'

const MAX_NODES_MOBILE = 320
const ASSOC_DIST = 6 // A, below this the drug counts as at the pocket
const MAX_HB = 8

function Protein({ series, tNsRef, accent, nodes, pocketIdx, rmsf, baseColors }: {
  series: MdSeries
  tNsRef: MutableRefObject<number>
  accent: string
  nodes: ResidueNode[]
  pocketIdx: Set<number>
  rmsf: number[]
  baseColors: THREE.Color[]
}) {
  const meshRef = useRef<THREE.InstancedMesh>(null)
  const dummy = useMemo(() => new THREE.Object3D(), [])
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
      const amp = 0.06 + 0.05 * (rmsf[i] ?? 0)
      const jitter = Math.sin(time * 1.6 + i * 1.7) * amp
      dummy.position.set(n.pos[0], n.pos[1] + jitter, n.pos[2])
      dummy.scale.setScalar(0.16)
      dummy.updateMatrix()
      mesh.setMatrixAt(i, dummy.matrix)
      const isLit = pocketIdx.has(i) && litLeft > 0
      if (isLit) litLeft--
      const color = isLit ? hot : baseColors[i]
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
  const geoRef = useRef<THREE.BufferGeometry>(null)
  // A mutable scratch buffer updated in place each frame. Kept in a ref so it is never read
  // during render: the react-hooks rules forbid mutating useMemo values and reading refs in render.
  const positionsRef = useRef(new Float32Array(MAX_HB * 2 * 3))
  const pocketArr = useMemo(() => [...pocketIdx], [pocketIdx])

  useEffect(() => {
    const geo = geoRef.current
    if (!geo) return
    geo.setAttribute('position', new THREE.BufferAttribute(positionsRef.current, 3))
    geo.setDrawRange(0, 0)
  }, [])

  useFrame(() => {
    const geo = geoRef.current
    if (!geo || pocketArr.length === 0) return
    const positions = positionsRef.current
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
    geo.setDrawRange(0, n * 2)
    const attr = geo.getAttribute('position') as THREE.BufferAttribute
    if (attr) attr.needsUpdate = true
  })

  return (
    <lineSegments>
      <bufferGeometry ref={geoRef} />
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
  const rmsf = useMemo(() => {
    const vals: number[] = []
    for (let i = 0; i < count; i++) vals.push(rmsfFor(series, i))
    return vals
  }, [series, count])
  const baseColors = useMemo(
    () => nodes.map((n) => new THREE.Color('#9fb3aa').lerp(new THREE.Color('#1f5740'), n.coreness)),
    [nodes],
  )
  const pocketIdx = useMemo(() => new Set(pocketNodeIndices(nodes, 14)), [nodes])
  return (
    <Canvas camera={{ position: [0, 6, 11], fov: 42 }} dpr={[1, 2]} style={{ height: '100%', width: '100%' }}>
      <ambientLight intensity={0.78} />
      <directionalLight position={[5, 8, 6]} intensity={1.0} />
      <directionalLight position={[-6, -2, -4]} intensity={0.36} />
      <Protein series={series} tNsRef={tNsRef} accent={accent} nodes={nodes} pocketIdx={pocketIdx} rmsf={rmsf} baseColors={baseColors} />
      <HBonds series={series} tNsRef={tNsRef} nodes={nodes} pocketIdx={pocketIdx} />
      <Ligand series={series} tNsRef={tNsRef} accent={accent} />
    </Canvas>
  )
}
