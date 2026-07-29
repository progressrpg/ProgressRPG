// vite.config.ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { fileURLToPath } from 'url'
import path from 'node:path'
import { storybookTest } from '@storybook/addon-vitest/vitest-plugin'
import { playwright } from '@vitest/browser-playwright'

const dirname = fileURLToPath(new URL('.', import.meta.url))

// PoC (issue #631) finding: several of NativeWind's/@react-native-aria's
// published CJS files (e.g. react-native-css-interop/dist/doctor.js) ship
// raw, un-transpiled JSX - the exact same class of upstream packaging bug
// #579's `@rn-primitives` PoC found (founded-labs/react-native-reusables#275),
// just in a different dependency. Same scoped esbuild-transform workaround.
function gluestackJsxWorkaround() {
  return {
    name: 'gluestack-jsx-workaround',
    enforce: 'pre' as const,
    async transform(code: string, id: string) {
      if (!/nativewind|react-native-css-interop|@react-native-aria|@gluestack-ui/.test(id)) return null;
      if (!/\.m?js$/.test(id)) return null;
      const esbuild = await import('esbuild');
      const result = await esbuild.transform(code, { loader: 'jsx', jsx: 'automatic' });
      return { code: result.code, map: result.map };
    },
  };
}

// https://vite.dev/config/
export default defineConfig(() => {
  return {
    plugins: [
      gluestackJsxWorkaround(),
      // PoC (issue #631) - the single most decisive finding of this spike,
      // left here as plain `react()` deliberately. Making the Gluestack
      // components' Tailwind classes actually apply requires
      // `react({ jsxImportSource: 'nativewind' })`: `cssInterop()` (called
      // per-component, scoped) only *registers* that a prop name maps to
      // styling - the actual `className` -> RN-style-object conversion
      // happens inside NativeWind's custom JSX pragma
      // (`react-native-css-interop`'s `jsx()`/`jsxs()` wrappers), which only
      // runs when `jsxImportSource` points at it for *every* file (verified:
      // with plain `react()`, a Gluestack Button's Tailwind classes produced
      // no styling at all - transparent background, 0 padding; switching to
      // `jsxImportSource: 'nativewind'` fixed that one component).
      //
      // But `jsxImportSource` is compiler-wide, not opt-in per file - and
      // turning it on breaks all 41 pre-existing unit test files across the
      // *entire* app (confirmed by actually doing it and running the full
      // suite): every JSX-emitting file now routes through
      // `nativewind/jsx-runtime` -> `react-native-css-interop`, which
      // requires `react-native` at module-init time, hitting the same raw
      // CJS `require("react-native")` wall documented in the `test.exclude`
      // comment below - except this time for the *whole app*, not just the
      // Gluestack ports. There is no working per-file middle ground in this
      // toolchain: it's "every file breaks in tests" or "Gluestack renders
      // unstyled." Left at the latter (safe) state; the former was used only
      // long enough to take the bundle-size and browser-behavior
      // measurements in the findings doc, then reverted here.
      react(),
    ],
    base: '/',
    resolve: {
      alias: {
        // PoC (issue #631): same as #629's PoC - @gluestack-ui packages and
        // NativeWind's interop layer import from 'react-native' internally;
        // this project is web-only, so alias it to react-native-web the way
        // Metro/webpack would for React Native Web.
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
            // PoC (issue #631) finding: OnlineCountBadge.gluestack.test.tsx
            // is excluded here, not just left to fail, because it can't be
            // fixed the way #579's equivalent issue was. Vitest externalizes
            // node_modules to plain Node resolution by default; `server.
            // deps.inline`/`ssr.noExternal` (forcing these through Vite's
            // own resolver, which does apply the `react-native` alias above)
            // was tried first - the same class of fix #579's
            // `@rn-primitives` PoC needed - and didn't work: several of
            // NativeWind's/@react-native-aria's dependencies do a raw CJS
            // `require("react-native")` deep in already-compiled output,
            // which resolves via Node's native module loader once Node's
            // CJS interop takes over - a boundary neither `resolve.alias`
            // nor `ssr.noExternal` nor `vi.mock` can reach (all three were
            // tried; confirmed via a stack trace showing `Module.require`,
            // not Vite's transform pipeline). Verification for the
            // Gluestack-ported components was done via a real Playwright
            // browser build instead - see findings doc.
            exclude: [
              'node_modules',
              'dist',
              'tests/**',
              '**/*.spec.{js,jsx,ts,tsx}',
              'src/components/OnlineCountBadge/OnlineCountBadge.gluestack.test.tsx',
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
