import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  build: {
    outDir: '../finclaw/web/static',
    emptyOutDir: true,
  },
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://localhost:8080',
      '/ws': {
        target: 'ws://localhost:8080',
        ws: true,
      },
    },
  },
})
