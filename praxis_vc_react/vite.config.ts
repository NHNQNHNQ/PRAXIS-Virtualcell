import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// dev 用相对路径 + proxy:前端(5173)请求 /api/* 由 Vite 转发到后端(默认 8000),
// 与生产同源托管行为一致。VITE_DEV_API 可覆盖后端地址。
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
