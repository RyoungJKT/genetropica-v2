// Assemble the unified deploy artifact.
//
// Vite builds the React dashboard into dist/app/ (base "/app/"). This script
// drops the static landing page at the dist/ root so a single Vercel output
// serves the landing at "/" and the dashboard at "/app".
import { cpSync, existsSync, mkdirSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const web = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const landing = resolve(web, 'landing')
const dist = resolve(web, 'dist')

mkdirSync(dist, { recursive: true })

const landingHtml = resolve(landing, 'index.html')
if (!existsSync(landingHtml)) {
  throw new Error(`[assemble] landing/index.html not found at ${landingHtml}`)
}
cpSync(landingHtml, resolve(dist, 'index.html'))

const landingAssets = resolve(landing, 'assets')
if (existsSync(landingAssets)) {
  cpSync(landingAssets, resolve(dist, 'assets'), { recursive: true })
}

console.log('[assemble] landing -> dist/ (site root); dashboard at dist/app/')
