import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { loadEnv } from 'vite'
import { defineConfig } from 'vitest/config'

export default defineConfig(({ mode }) => {
  // Fail the production build (instead of shipping a blank page) when the API URL is missing.
  if (mode === 'production' && !loadEnv(mode, process.cwd(), 'VITE_').VITE_API_URL) {
    throw new Error('VITE_API_URL must be set for production builds')
  }
  return {
    plugins: [react(), tailwindcss()],
    test: {
      environment: 'jsdom',
      setupFiles: ['./src/test/setup.ts'],
      coverage: {
        provider: 'v8',
        include: ['src/**'],
        exclude: ['src/main.tsx', 'src/api/schema.d.ts', 'src/test/**', 'src/**/*.test.*'],
        thresholds: { lines: 80, functions: 80, statements: 80, branches: 70 },
      },
    },
  }
})
