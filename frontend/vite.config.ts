import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'node:path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { '@': path.resolve(__dirname, './src') },
  },
  server: {
    // 5174 is the single, canonical frontend port for this project. Docker's
    // published port is also 5174, so only one of (manual `npm run dev`,
    // Docker container) can be running at a time. strictPort makes that
    // conflict fail loudly instead of silently drifting to 5175+.
    port: 5174,
    strictPort: true,
    host: true,
    // Dev proxies /api to the local FastAPI process, so no CORS config is
    // needed while developing. In Docker, nginx does the same job.
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  build: { outDir: 'dist', sourcemap: false },
})
