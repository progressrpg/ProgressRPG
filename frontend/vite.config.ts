// vite.config.ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { fileURLToPath } from 'url'
import path from 'node:path'
import { storybookTest } from '@storybook/addon-vitest/vitest-plugin'
import { playwright } from '@vitest/browser-playwright'

const dirname = fileURLToPath(new URL('.', import.meta.url))

// https://vite.dev/config/
// PoC for issue #579: the published @rn-primitives/* packages ship raw,
// un-transpiled JSX inside their `.mjs`/`.js` output (a known upstream
// packaging bug - see founded-labs/react-native-reusables#275), which Vite's
// default loader mapping (by file extension) can't parse. This forces esbuild
// to treat those specific files as JSX so the PoC can build at all.
function rnPrimitivesJsxWorkaround() {
  return {
    name: 'rn-primitives-jsx-workaround',
    enforce: 'pre' as const,
    async transform(code: string, id: string) {
      if (!id.includes('@rn-primitives') && !id.includes('react-native-web')) return null;
      if (!/\.m?js$/.test(id)) return null;
      const esbuild = await import('esbuild');
      const result = await esbuild.transform(code, { loader: 'jsx', jsx: 'automatic' });
      return { code: result.code, map: result.map };
    },
  };
}

export default defineConfig(() => {
  return {
    plugins: [react(), rnPrimitivesJsxWorkaround()],
    base: '/',
    resolve: {
      alias: {
        // PoC for issue #579: @rn-primitives packages import from
        // 'react-native' internally; this project is web-only, so alias it
        // to react-native-web the same way Metro/webpack would for RN Web.
        'react-native': 'react-native-web',
      },
      // @rn-primitives packages ship platform-specific files (e.g.
      // `tooltip.web.mjs` vs `tooltip.mjs`) and rely on the bundler resolving
      // `.web.*` first, the way Metro/webpack do for react-native-web. Vite
      // has no built-in notion of this, so it has to be told explicitly.
      extensions: ['.web.mjs', '.web.js', '.mjs', '.js', '.mts', '.ts', '.jsx', '.tsx', '.json'],
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
            // PoC for issue #579: @rn-primitives' internal `import './tooltip'`
            // (no extension) relies on a bundler resolving platform-specific
            // files; Vitest externalizes node_modules to plain Node ESM
            // resolution by default, which can't do that. Forcing it through
            // Vite's own resolver (which does have the .web.* extensions
            // above) fixes it.
            server: {
              deps: {
                inline: [/@rn-primitives\//, 'react-native-web'],
              },
            },
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
