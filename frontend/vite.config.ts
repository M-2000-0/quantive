/// <reference types="vitest" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  base: './',
  plugins: [react(), tailwindcss()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    css: true,
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      include: ['src/**/*.{ts,tsx}'],
      exclude: [
        'src/test/**',
        'src/**/*.test.{ts,tsx}',
        'src/**/*.d.ts',
        'src/main.tsx',
        'src/pwa.ts',
        'src/pages/NewPortfolioPage.tsx',
        'src/utils/decisionPackagePdf.ts',
      ],
      thresholds: {
        lines: 9,
        functions: 8,
        branches: 5,
        statements: 9,
      },
    },
  },
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
