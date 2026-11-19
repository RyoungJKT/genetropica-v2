/// <reference types="vitest/config" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  // The dashboard is mounted under /app; the static landing page is served at the site root.
  base: '/app/',
  plugins: [
    react(),
    {
      name: 'omit-3dmol-shader-note',
      enforce: 'pre',
      transform: {
        filter: { id: /\/node_modules\/3dmol\/build\/3Dmol\.js$/ },
        handler(source) {
          // The GLSL is embedded in a string, so JS minification preserves its comments.
          return source.replace(/\/\/code for pseudorandom vector from [^\\\r\n]+(?=\\nfloat hash\()/, '')
        },
      },
    },
  ],
  build: { outDir: 'dist/app' },
  test: { environment: 'node', include: ['src/**/*.test.ts'], passWithNoTests: true },
})
