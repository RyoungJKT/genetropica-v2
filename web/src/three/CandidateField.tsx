import { useRef, useState } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { OrbitControls } from '@react-three/drei'
import { useReducedMotion } from 'framer-motion'
import * as THREE from 'three'
import type { FieldPoint } from '../data/types'
import { bucketOf, insight } from '../lib/buckets'

const sx = (v: number) => (((-v) - 4) / (9 - 4)) * 16 - 8 // stronger binding to the right
const sy = (le: number) => ((le - 0.08) / (0.3 - 0.08)) * 13 - 5
const sz = (mw: number) => ((mw - 150) / (1300 - 150)) * 16 - 8
const rad = (ha: number) => 0.28 + (ha / 79) * 0.85

function Cloud({ points, onHover, reduce }: { points: FieldPoint[]; onHover: (p: FieldPoint | null) => void; reduce: boolean }) {
  const g = useRef<THREE.Group>(null)
  const t0 = useRef(0)
  useFrame((s) => {
    if (!g.current) return
    if (reduce) {
      g.current.scale.setScalar(1)
      return
    }
    if (t0.current === 0) t0.current = s.clock.elapsedTime
    const p = Math.min(1, (s.clock.elapsedTime - t0.current) / 1.1)
    g.current.scale.setScalar(1 - Math.pow(1 - p, 3))
  })
  return (
    <group ref={g}>
      {points.map((pt) => {
        const pos: [number, number, number] = [sx(pt.vina), sy(pt.le ?? 0.15), sz(pt.mw)]
        const r = rad(pt.ha)
        const col = bucketOf(pt).color
        return (
          <group key={pt.name} position={pos}>
            <mesh
              onPointerOver={(e) => { e.stopPropagation(); onHover(pt) }}
              onPointerOut={() => onHover(null)}
            >
              <sphereGeometry args={[r, 24, 24]} />
              <meshStandardMaterial color={col} transparent opacity={pt.admet ? 0.96 : 0.42} roughness={0.35} metalness={0.05} />
            </mesh>
            {pt.dl === 1 && (
              <mesh>
                <torusGeometry args={[r + 0.12, 0.035, 10, 36]} />
                <meshBasicMaterial color="#2E7D5B" />
              </mesh>
            )}
          </group>
        )
      })}
    </group>
  )
}

export function CandidateField({ points }: { points: FieldPoint[] }) {
  const reduce = !!useReducedMotion()
  const [hover, setHover] = useState<FieldPoint | null>(null)
  const [xy, setXY] = useState({ x: 0, y: 0 })
  const b = hover ? bucketOf(hover) : null
  return (
    <div
      style={{
        position: 'relative', width: '100%', height: 560,
        border: '1px solid var(--line)', borderRadius: 18, overflow: 'hidden',
        background: 'radial-gradient(120% 90% at 30% 10%, #fbf8ef 0%, #efe9da 60%, #e7e0cf 100%)',
        cursor: 'grab',
      }}
      onPointerMove={(e) => {
        const r = e.currentTarget.getBoundingClientRect()
        setXY({ x: e.clientX - r.left, y: e.clientY - r.top })
      }}
    >
      <Canvas camera={{ position: [9, 7, 16], fov: 50 }} dpr={[1, 2]}>
        <ambientLight intensity={0.85} />
        <directionalLight position={[6, 12, 8]} intensity={0.7} />
        <gridHelper args={[20, 20, '#cdbfae', '#ddd3c0']} position={[0, -5.4, 0]} />
        <Cloud points={points} onHover={setHover} reduce={reduce} />
        <OrbitControls
          enableDamping dampingFactor={0.08} enablePan={false}
          minDistance={10} maxDistance={30}
          autoRotate={!hover && !reduce} autoRotateSpeed={0.7}
          target={[0, 1.5, 0]}
        />
      </Canvas>
      <div style={{ position: 'absolute', top: 14, left: 16, fontFamily: 'var(--mono)', fontSize: 10, letterSpacing: '.08em', textTransform: 'uppercase', color: 'var(--ink-faint)', pointerEvents: 'none' }}>
        Drag to rotate, hover a sphere
      </div>
      {hover && b && (
        <div
          style={{
            position: 'absolute', left: Math.min(xy.x + 16, 360), top: xy.y + 10,
            width: 230, background: 'var(--ink)', color: 'var(--paper)', borderRadius: 12,
            padding: '14px 15px', boxShadow: '0 18px 40px rgba(28,26,23,.28)', pointerEvents: 'none', zIndex: 5,
          }}
        >
          <div style={{ fontFamily: 'var(--serif)', fontSize: 19, textTransform: 'capitalize' }}>{hover.name.replace(/_/g, ' ')}</div>
          <div style={{ fontFamily: 'var(--mono)', fontSize: 9.5, letterSpacing: '.08em', textTransform: 'uppercase', color: b.color, marginTop: 2 }}>{b.label}</div>
          <div style={{ fontSize: 12.5, color: '#e8e0d2', marginTop: 8 }}>Approved for: <b style={{ color: '#fff' }}>{hover.indication}</b></div>
          <Row k="Binding (Vina)" v={`${hover.vina} kcal/mol`} />
          <Row k="Efficiency / atom" v={hover.le !== null ? hover.le.toFixed(3) : 'n/a'} />
          <Row k="Size" v={`${Math.round(hover.mw)} Da, ${hover.ha} atoms`} />
          <Row k="Drug-like, Safe" v={`${hover.dl ? 'yes' : 'no'}, ${hover.admet ? 'pass' : 'flag'}`} />
          <div style={{ fontSize: 13, lineHeight: 1.5, marginTop: 10, borderTop: '1px solid #3a352d', paddingTop: 9, color: '#f4f0e6' }}>{insight(hover)}</div>
        </div>
      )}
    </div>
  )
}

function Row({ k, v }: { k: string; v: string }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', fontFamily: 'var(--mono)', fontSize: 11, color: '#cdbfae', marginTop: 5 }}>
      <span>{k}</span><b style={{ color: '#fff', fontWeight: 500 }}>{v}</b>
    </div>
  )
}
