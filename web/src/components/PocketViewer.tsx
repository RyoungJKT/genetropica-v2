import { useMemo } from 'react'
import { Canvas } from '@react-three/fiber'
import { OrbitControls } from '@react-three/drei'
import * as THREE from 'three'
import type { BindingData } from '../data/types'

const CPK: Record<string, string> = {
  C: '#3f3a33', H: '#e8e2d4', N: '#2e5bff', O: '#c0392b', S: '#c9a227',
  F: '#5fae3a', CL: '#3fa63f', P: '#d2691e', BR: '#8b4a2b', I: '#7a2f8a',
}
const cpk = (el: string) => CPK[el] ?? '#7a6f5c'
const arad = (el: string) => (el === 'H' ? 0.2 : 0.32)

function Molecule({ data }: { data: BindingData }) {
  const bonds = useMemo(
    () =>
      data.bonds.map(([i, j]) => {
        const a = data.ligand[i]
        const b = data.ligand[j]
        const va = new THREE.Vector3(a.x, a.y, a.z)
        const vb = new THREE.Vector3(b.x, b.y, b.z)
        const mid = va.clone().add(vb).multiplyScalar(0.5)
        const dir = vb.clone().sub(va)
        const len = dir.length()
        const q = new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 1, 0), dir.clone().normalize())
        return { mid: [mid.x, mid.y, mid.z] as [number, number, number], len, q: [q.x, q.y, q.z, q.w] as [number, number, number, number] }
      }),
    [data],
  )
  return (
    <group>
      {data.ligand.map((a, i) => (
        <mesh key={`a${i}`} position={[a.x, a.y, a.z]}>
          <sphereGeometry args={[arad(a.el), 20, 20]} />
          <meshStandardMaterial color={cpk(a.el)} roughness={0.4} metalness={0.05} />
        </mesh>
      ))}
      {bonds.map((b, i) => (
        <mesh key={`b${i}`} position={b.mid} quaternion={b.q}>
          <cylinderGeometry args={[0.09, 0.09, b.len, 10]} />
          <meshStandardMaterial color="#9a8f7a" roughness={0.6} />
        </mesh>
      ))}
    </group>
  )
}

export function PocketViewer({ data }: { data: BindingData }) {
  return (
    <div style={{ width: '100%', height: 480, border: '1px solid var(--line)', borderRadius: 18, overflow: 'hidden', background: 'radial-gradient(120% 90% at 30% 10%, #fbf8ef 0%, #efe9da 60%, #e7e0cf 100%)', cursor: 'grab' }}>
      <Canvas camera={{ position: [0, 0, 14], fov: 45 }} dpr={[1, 2]}>
        <ambientLight intensity={0.8} />
        <directionalLight position={[6, 8, 10]} intensity={0.85} />
        <directionalLight position={[-6, -4, -6]} intensity={0.3} />
        <Molecule data={data} />
        <OrbitControls enableDamping dampingFactor={0.1} enablePan={false} minDistance={5} maxDistance={30} />
      </Canvas>
    </div>
  )
}
