// vite.config.ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { fileURLToPath } from 'url'
import path from 'node:path'
import { storybookTest } from '@storybook/addon-vitest/vitest-plugin'
import { playwright } from '@vitest/browser-playwright'
import { viteStaticCopy } from 'vite-plugin-static-copy'
import { tamaguiPlugin } from '@tamagui/vite-plugin'

const dirname = fileURLToPath(new URL('.', import.meta.url))

// https://vite.dev/config/
export default defineConfig(() => {
  return {
    plugins: [
      react(),
      // maplibre-gl loads its own tile-processing worker via a runtime
      // `new URL('./maplibre-gl-worker.mjs', import.meta.url)` where the
      // filename is a variable, not a string literal Rollup can statically
      // resolve - so the production build never emits that file (or its
      // own sibling import, maplibre-gl-shared.mjs), and the map silently
      // renders zero vector layers (fills/lines) in production while DOM
      // markers keep working, since they don't go through the worker at
      // all (issue #624 investigation, 2026-07-31). optimizeDeps.exclude
      // above only fixes the equivalent dev-server-only version of this
      // problem. Copying both files verbatim (same relative names, so the
      // worker's own `./maplibre-gl-shared.mjs` import still resolves) and
      // pointing setWorkerUrl at the copy (see Map.tsx) is MapLibre's own
      // documented workaround for bundlers that can't auto-detect this.
      viteStaticCopy({
        targets: [
          {
            src: 'node_modules/maplibre-gl/dist/maplibre-gl-worker.mjs',
            dest: 'maplibre-gl',
            rename: { stripBase: true },
          },
          {
            src: 'node_modules/maplibre-gl/dist/maplibre-gl-shared.mjs',
            dest: 'maplibre-gl',
            rename: { stripBase: true },
          },
        ],
      }),
      // Activates Tamagui's compiler (extracts static styles at build time
      // instead of shipping a runtime style engine) for the RN/Expo
      // migration (#578/#591, decided in #591; first landed by #580).
      // Without this plugin, `tamagui`/`@tamagui/core` still work but every
      // style is computed at runtime instead - a materially worse bundle/
      // perf profile than what #629's PoC measured.
      tamaguiPlugin({
        config: './tamagui.config.ts',
        components: ['tamagui'],
      }),
    ],
    base: '/',
    // maplibre-gl loads its own worker via a dynamically-constructed URL;
    // Vite's dependency pre-bundler rewrites that URL to a path
    // (maplibre-gl-worker.mjs) it never actually emits, breaking the map at
    // runtime ("The file does not exist ... in the optimize deps
    // directory"). Excluding it from pre-bundling avoids the rewrite - this
    // is MapLibre's own documented workaround for Vite.
    optimizeDeps: {
      exclude: ['maplibre-gl'],
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
