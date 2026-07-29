// vite.config.ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { fileURLToPath } from 'url'
import path from 'node:path'
import { storybookTest } from '@storybook/addon-vitest/vitest-plugin'
import { playwright } from '@vitest/browser-playwright'
import { tamaguiPlugin } from '@tamagui/vite-plugin'

const dirname = fileURLToPath(new URL('.', import.meta.url))

// https://vite.dev/config/
export default defineConfig(() => {
  return {
    plugins: [
      react(),
      // PoC (issue #629): activates Tamagui's compiler (extracts static
      // styles at build time instead of shipping a runtime style engine).
      // Without this plugin, `tamagui`/`@tamagui/core` still work but every
      // style is computed at runtime - a materially different bundle/perf
      // profile from what's being measured below.
      tamaguiPlugin({
        config: './tamagui.config.ts',
        components: ['tamagui'],
      }),
    ],
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
      projects: [
        {
          extends: true,
          test: {
            name: 'unit',
            globals: true,
            environment: 'happy-dom',
            // Iframes (e.g. YouTube embeds in TutorialModal) otherwise attempt a
            // real network navigation in happy-dom, which aborts on test cleanup
            // and logs noisy DOMException stack traces with no effect on results.
            environmentOptions: {
              happyDOM: {
                settings: {
                  navigation: {
                    disableChildFrameNavigation: true,
                  },
                },
              },
            },
            setupFiles: './src/test/setup.js',
            css: true,
            exclude: ['node_modules', 'dist', 'tests/**', '**/*.spec.{js,jsx,ts,tsx}'],
          },
        },
        {
          extends: true,
          plugins: [
            storybookTest({ configDir: path.join(dirname, '.storybook') }),
          ],
          test: {
            name: 'storybook',
            browser: {
              enabled: true,
              headless: true,
              provider: playwright({}),
              instances: [{ browser: 'chromium' }],
            },
          },
        },
      ],
    },
  }
})
