import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// 本地 dev 跑前端，/api 与 /ws 代理到测试机 backend（改成 sh-2c2g 的地址或 localhost:8000）
const API_TARGET = process.env.VITE_API_TARGET || 'http://localhost:8000'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      '/api': { target: API_TARGET, changeOrigin: true },
      '/ws': { target: API_TARGET, ws: true, changeOrigin: true },
    },
  },
})
