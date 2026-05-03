// vite.config.js
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { fileURLToPath } from 'url'

// https://vite.dev/config/
export default defineConfig(() => {
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
      outDir: fileURLToPath(new URL('./dist', import.meta.url)),
      assetsDir: 'assets',
      emptyOutDir: true,
      manifest: true,
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
