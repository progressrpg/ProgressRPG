export const BASE_URL = process.env.PLAYWRIGHT_BASE_URL ?? 'http://localhost:5173';
export const API_URL = process.env.PLAYWRIGHT_API_URL ?? 'http://localhost:8000/api/v1';
export const TEST_EMAIL = process.env.PLAYWRIGHT_TEST_EMAIL ?? 'playwright@example.com';
export const TEST_PASSWORD = process.env.PLAYWRIGHT_TEST_PASSWORD ?? 'correcthorsebatterystaple';
export const TEST_USER_STORAGE_STATE_PATH = 'playwright/.auth/user.json';

export interface TestUser {
  email: string;
  password: string;
  playerName: string;
  storageStatePath: string;
}

const [TEST_EMAIL_LOCAL, TEST_EMAIL_DOMAIN] = TEST_EMAIL.split('@');

export const DEFAULT_USER: TestUser = {
  email: TEST_EMAIL,
  password: TEST_PASSWORD,
  playerName: 'Playwright Hero',
  storageStatePath: TEST_USER_STORAGE_STATE_PATH,
};

/**
 * Playwright runs every spec file once per matching project (fullyParallel:
 * true), and playwright.config.ts's chromium/firefox/webkit projects have no
 * testMatch filter - they all run every spec file concurrently, plus a 4th
 * `a11y` project for the two a11y-named files. So the real unit of
 * concurrency is (spec file x project), not just the spec file: a user
 * dedicated only per file would still be shared across 3-4 simultaneous
 * browser contexts.
 */
export const PROJECT_NAMES = ['chromium', 'firefox', 'webkit', 'a11y'] as const;
export type ProjectName = (typeof PROJECT_NAMES)[number];

/**
 * One ActivityTimer per player (OneToOneField), broadcast over a single
 * WebSocket channel per player - any two (spec file, project) runs sharing a
 * user can race Start/Stop/label calls against each other and against WS
 * pushes meant for the other run. Every spec file that touches /timer gets
 * its own user per project so concurrent runs never share timer state.
 * Files that only exercise unrelated pages keep using `DEFAULT_USER`.
 *
 * The slug list below must stay in sync with PLAYWRIGHT_SUITE_SLUGS in
 * users/management/commands/seed_playwright_user.py, which seeds the
 * matching backend users (one per slug x project) in one `--all` invocation.
 */
export const TIMER_SUITE_SLUGS = [
  'a11y-pages',
  'a11y-tasks',
  'accessibility',
  'auth-logout',
  'tasks-core-loop',
  'tasks-projects',
  'timer',
  'unified-timer-home',
  'smoke-pages',
] as const;
export type TimerSuiteSlug = (typeof TIMER_SUITE_SLUGS)[number];

export function derivedUser(slug: string, project: string): TestUser {
  const key = `${slug}-${project}`;
  return {
    email: `${TEST_EMAIL_LOCAL}+${key}@${TEST_EMAIL_DOMAIN}`,
    password: TEST_PASSWORD,
    playerName: `Playwright ${key}`,
    storageStatePath: `playwright/.auth/${key}.json`,
  };
}

/**
 * Value for `test.use({ storageState: ... })` that resolves to the dedicated
 * user for the given suite slug, keyed by the project the test is actually
 * running under (testInfo.project.name) - not just the spec file.
 */
export function timerUserStorageState(slug: TimerSuiteSlug) {
  return async (
    {}: object,
    use: (path: string) => Promise<void>,
    testInfo: { project: { name: string } },
  ) => {
    await use(derivedUser(slug, testInfo.project.name).storageStatePath);
  };
}
