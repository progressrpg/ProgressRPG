import { defineConfig, devices } from '@playwright/test';

import { BASE_URL } from './playwright/testUser';

/**
 * See https://playwright.dev/docs/test-configuration.
 */
export default defineConfig({
  globalSetup: './playwright/global-setup.ts',
  testDir: './tests',
  /* Run tests in files in parallel */
  fullyParallel: true,
  /* Fail the build on CI if you accidentally left test.only in the source code. */
  forbidOnly: !!process.env.CI,
  /* Retry on CI only */
  retries: process.env.CI ? 2 : 1,
  /* Opt out of parallel tests on CI. */
  // Locally, cap workers rather than leaving Playwright's CPU-based auto
  // default (often 8+): every project (chromium/firefox/webkit/a11y) shares
  // one single-process Daphne dev backend (compose.yaml), and too many
  // concurrent browser contexts saturate it, surfacing as scattered,
  // feature-agnostic flakiness across unrelated specs (fail-then-pass on
  // retry) rather than any one test's bug.
  workers: process.env.CI ? 1 : 4,
  /* Reporter to use. See https://playwright.dev/docs/test-reporters */
  reporter: 'html',

  /* Shared settings for all the projects below. See https://playwright.dev/docs/api/class-testoptions. */
  use: {
    /* Base URL to use in actions like `await page.goto('/')`. */
    baseURL: BASE_URL,

    /* Collect trace when retrying the failed test. See https://playwright.dev/docs/trace-viewer */
    trace: 'on-first-retry',
  },

  /* Configure projects for major browsers */
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },

    {
      name: 'firefox',
      use: {
        ...devices['Desktop Firefox'],
        actionTimeout: 15000,
        navigationTimeout: 20000,
      },
    },

    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },

    // Add accessibility testing project
    {
      name: 'a11y',
      testMatch: /.*a11y.*\.spec\.ts/,
      use: { ...devices['Desktop Chrome'] },
    },
  ],

  /* Run your local dev server before starting the tests */
  webServer: {
    command: 'npm run dev',
    url: BASE_URL,
    reuseExistingServer: !process.env.CI,
  },
});
