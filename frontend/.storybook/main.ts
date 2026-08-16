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
