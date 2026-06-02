import { useEffect, useRef } from 'react'
import * as $3Dmol from '3dmol'
import type { Contact } from '../data/types'

export function Mol3DViewer({ receptorUrl, ligandUrl, contacts }: { receptorUrl: string; ligandUrl: string; contacts: Contact[] }) {
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const el = ref.current
    if (!el) return
    let cancelled = false
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    let viewer: any
    el.innerHTML = ''
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    viewer = ($3Dmol as any).createViewer(el, { backgroundColor: '#efe9da' })

    Promise.all([
      fetch(receptorUrl).then((r) => (r.ok ? r.text() : '')),
      fetch(ligandUrl).then((r) => (r.ok ? r.text() : '')),
    ]).then(([pdb, mol]) => {
      if (cancelled || !viewer) return
      if (pdb) {
        viewer.addModel(pdb, 'pdb')
        viewer.setStyle({}, { cartoon: { color: '#a9bcae', opacity: 0.65 } })
        const resi = contacts.map((c) => parseInt(c.num, 10)).filter((n) => !Number.isNaN(n))
        if (resi.length) {
          viewer.setStyle({ resi }, { stick: { radius: 0.12, colorscheme: 'whiteCarbon' }, cartoon: { color: '#a9bcae', opacity: 0.65 } })
        }
      }
      const lig = viewer.addModel(mol, 'mol')
      const ligModel = lig.getID ? lig.getID() : undefined
      viewer.setStyle({ model: ligModel }, { stick: { radius: 0.16 }, sphere: { scale: 0.26 } })
      viewer.zoomTo({ model: ligModel })
      viewer.zoom(0.85)
      viewer.render()
    })

    return () => {
      cancelled = true
      try {
        if (viewer) viewer.clear()
      } catch {
        /* noop */
      }
      if (el) el.innerHTML = ''
    }
  }, [receptorUrl, ligandUrl, contacts])

  return (
    <div
      ref={ref}
      style={{ position: 'relative', width: '100%', height: 480, border: '1px solid var(--line)', borderRadius: 18, overflow: 'hidden', background: '#efe9da' }}
    />
  )
}
