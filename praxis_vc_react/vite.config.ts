import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const DEV_API = process.env.VITE_DEV_API || 'http://127.0.0.1:8000'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': { target: DEV_API, changeOrigin: true },
    },
  },
})
