import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const LOGISTICA = process.env.LOGISTICA_API_URL ?? 'http://localhost:8001'
const CAUTELA = process.env.CAUTELA_API_URL ?? 'http://localhost:8002'

// O navegador fala só com o Vite; o proxy encaminha para cada sistema.
export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
    proxy: {
      '/logistica': { target: LOGISTICA, rewrite: (p) => p.replace(/^\/logistica/, '') },
      '/cautela': { target: CAUTELA, rewrite: (p) => p.replace(/^\/cautela/, '') },
    },
  },
})
