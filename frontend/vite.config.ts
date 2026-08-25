import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  build: {
    // Allow optional peer deps (jspdf, html2canvas, xlsx) to be missing at build time —
    // Phase 1d uses dynamic import + fallback to markdown, so hard failure is not desired.
    // @ts-ignore rolldownOptions is valid in Vite 7+/rolldown
    rolldownOptions: {
      external: ['jspdf', 'html2canvas', 'xlsx'],
    },
    rollupOptions: {
      external: ['jspdf', 'html2canvas', 'xlsx'],
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
