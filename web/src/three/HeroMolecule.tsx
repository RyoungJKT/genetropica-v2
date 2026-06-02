import { useRef } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { useReducedMotion } from 'framer-motion'
import * as THREE from 'three'

const PTS: [number, number, number][] = [
  [0, 0, 0], [2.6, 0.6, 0.4], [-2.4, 1.1, -0.6], [0.8, 2.6, -1.2], [-0.9, -2.6, 0.9],
  [2.0, -1.8, 1.4], [-2.2, -1.4, -1.6], [0.3, 1.2, 3.0], [1.4, -0.4, -2.8],
]

function Mol({ reduce }: { reduce: boolean }) {
  const g = useRef<THREE.Group>(null)
  useFrame((s) => {
    if (g.current && !reduce) {
      const t = s.clock.elapsedTime * 0.4
      g.current.rotation.y = t
      g.current.rotation.x = Math.sin(t * 0.65) * 0.25
    }
  })
  return (
    <group ref={g}>
      {PTS.map((p, i) => (
        <mesh key={`a${i}`} position={p}>
          <sphereGeometry args={[i === 0 ? 0.95 : 0.6, 32, 32]} />
          <meshStandardMaterial color={i % 4 === 0 ? '#A8492B' : '#1F5740'} roughness={0.4} metalness={0.1} />
        </mesh>
      ))}
      {PTS.slice(1).map((p, i) => {
        const a = new THREE.Vector3(...PTS[0])
        const b = new THREE.Vector3(...p)
        const d = b.clone().sub(a)
        const len = d.length()
        const mid = a.clone().add(b).multiplyScalar(0.5)
        const q = new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 1, 0), d.clone().normalize())
        return (
          <mesh key={`b${i}`} position={[mid.x, mid.y, mid.z]} quaternion={[q.x, q.y, q.z, q.w]}>
            <cylinderGeometry args={[0.07, 0.07, len, 12]} />
            <meshStandardMaterial color="#6f8a7c" roughness={0.6} />
          </mesh>
        )
      })}
    </group>
  )
}

export function HeroMolecule() {
  const reduce = !!useReducedMotion()
  return (
    <div style={{ width: '100%', height: '100%', minHeight: 360 }}>
      <Canvas camera={{ position: [0, 0, 15], fov: 45 }} dpr={[1, 2]}>
        <ambientLight intensity={0.7} />
        <directionalLight position={[5, 6, 8]} intensity={0.9} />
        <directionalLight position={[-6, -3, 2]} intensity={0.4} color="#A8742C" />
        <Mol reduce={reduce} />
      </Canvas>
    </div>
  )
}
