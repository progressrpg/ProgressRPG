// vite.config.js
import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

const isProduction = process.env.NODE_ENV === 'production'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const isProd = mode === 'production'

  return {
    plugins: [react()],
    base: '/',
    server: {
      open: true,
      host: true,
      proxy: {
        '/api': {
          target: 'http://localhost:8000',
          changeOrigin: true,
          secure: false,
        }
      }
    },
    build: {
      outDir: path.resolve(__dirname, './dist'),
      assetsDir: 'assets',
      emptyOutDir: true,
      manifest: true,
      rollupOptions: {
        input: 'src/main.jsx',
      },
    },
    test: {
      globals: true,
      environment: 'happy-dom',
      setupFiles: './src/test/setup.js',
      css: true,
      exclude: ['node_modules', 'dist', 'tests/**', '**/*.spec.{js,jsx}'],
    },
  }
})
