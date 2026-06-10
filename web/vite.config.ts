/// <reference types="vitest/config" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  // The dashboard is mounted under /app; the static landing page is served at the site root.
  base: '/app/',
  plugins: [react()],
  build: { outDir: 'dist/app' },
  test: { environment: 'node', include: ['src/**/*.test.ts'], passWithNoTests: true },
})
