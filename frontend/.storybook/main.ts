import type { StorybookConfig } from '@storybook/react-vite';

const config: StorybookConfig = {
  stories: ['../src/**/*.stories.@(js|jsx|ts|tsx)'],
  addons: [
    '@storybook/addon-a11y',
    '@storybook/addon-docs',
    '@storybook/addon-vitest'
  ],
  framework: '@storybook/react-vite',
  viteFinal: async (config, options) => {
    // src/config.ts requires an explicit VITE_API_BASE_URL and throws without
    // one (#571). Stories never call the backend, but some of them do pull in
    // modules that import it transitively (Footer renders an /admin link), and
    // the static build runs in production mode, so no .env.<mode> file supplies
    // a value. Give it an obviously-local placeholder rather than letting the
    // gallery white-screen on a config error it has no stake in.
    config.define = {
      ...config.define,
      'import.meta.env.VITE_API_BASE_URL': JSON.stringify(
        process.env.VITE_API_BASE_URL || 'http://localhost:8000',
      ),
    };
    // Only the static build (deployed to GitHub Pages under the repo name)
    // needs this subpath base. Dev server and @storybook/addon-vitest's
    // browser test runner both reuse this same viteFinal, and serving them
    // under a non-root base breaks the vitest browser client's handshake
    // with the page (it times out with "Failed to connect to the browser
    // session"), so leave base untouched outside of production builds.
    if (options.configType === 'PRODUCTION') {
      config.base = '/ProgressRPG/storybook/';
    }
    return config;
  }
};

export default config;
