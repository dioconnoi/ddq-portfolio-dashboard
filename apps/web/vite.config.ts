import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { loadEnv } from 'vite'
import { defineConfig } from 'vitest/config'
import { resolveApiUrl } from './src/apiUrl.ts'

export default defineConfig(({ command, mode }) => {
  // Fail every production build (any --mode) on a missing or malformed API URL, instead of
  // shipping a bundle that throws on load.
  if (command === 'build') {
    resolveApiUrl(loadEnv(mode, process.cwd(), 'VITE_').VITE_API_URL, true)
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
