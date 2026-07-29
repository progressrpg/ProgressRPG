// vite.config.ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { fileURLToPath } from 'url'
import path from 'node:path'
import { storybookTest } from '@storybook/addon-vitest/vitest-plugin'
import { playwright } from '@vitest/browser-playwright'

const dirname = fileURLToPath(new URL('.', import.meta.url))

// https://vite.dev/config/
export default defineConfig(() => {
  return {
    plugins: [react()],
    base: '/',
    resolve: {
      alias: {
        // PoC (Restyle vs Tamagui/Gluestack/@rn-primitives): @shopify/restyle
        // imports from 'react-native' internally (StyleSheet, View, Text,
        // Pressable); this project is web-only, so alias it to
        // react-native-web the same way Metro/webpack would for RN Web -
        // same pattern the other three PoCs needed.
        'react-native': 'react-native-web',
      },
    },
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
            // PoC (Restyle) finding: OnlineCountBadge.restyle.test.tsx and
            // Button.restyle.test.tsx are excluded here, not just left to
            // fail - same wall the Gluestack PoC hit, confirmed by actually
            // trying all three documented fixes, not assumed. @shopify/
            // restyle's compiled dist/index.js does a raw CJS
            // require('react-native') at module-init time; Vitest
            // externalizes node_modules to plain Node resolution by
            // default, and none of `server.deps.inline`, `ssr.noExternal`,
            // nor `vi.mock('react-native', ...)` reach it - confirmed via a
            // stack trace showing Node's own `Module.require`/
            // `loadESMFromCJS`, not Vite's transform pipeline (same
            // boundary, same class of dependency as the Gluestack PoC's
            // react-native-css-interop). Verification for the Restyle-ported
            // components was done via a real Playwright browser build
            // instead - see findings doc.
            exclude: [
              'node_modules',
              'dist',
              'tests/**',
              '**/*.spec.{js,jsx,ts,tsx}',
              'src/components/OnlineCountBadge/OnlineCountBadge.restyle.test.tsx',
              'src/components/Button/Button.restyle.test.tsx',
            ],
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
