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

function derivedUser(slug: string): TestUser {
  return {
    email: `${TEST_EMAIL_LOCAL}+${slug}@${TEST_EMAIL_DOMAIN}`,
    password: TEST_PASSWORD,
    playerName: `Playwright ${slug}`,
    storageStatePath: `playwright/.auth/${slug}.json`,
  };
}

/**
 * One ActivityTimer per player (OneToOneField), broadcast over a single
 * WebSocket channel per player - any two spec files sharing a user and
 * running concurrently (fullyParallel: true) can race Start/Stop/label
 * calls against each other and against WS pushes meant for the other
 * test. Every spec file that touches /timer gets its own dedicated user
 * so concurrent runs never share timer state. Files that only exercise
 * unrelated pages keep using `default`.
 */
export const TEST_USERS = {
  default: { email: TEST_EMAIL, password: TEST_PASSWORD, playerName: 'Playwright Hero', storageStatePath: TEST_USER_STORAGE_STATE_PATH },
  'a11y-pages': derivedUser('a11y-pages'),
  'a11y-tasks': derivedUser('a11y-tasks'),
  accessibility: derivedUser('accessibility'),
  'auth-logout': derivedUser('auth-logout'),
  'tasks-core-loop': derivedUser('tasks-core-loop'),
  'tasks-projects': derivedUser('tasks-projects'),
  timer: derivedUser('timer'),
  'unified-timer-home': derivedUser('unified-timer-home'),
  'smoke-pages': derivedUser('smoke-pages'),
} satisfies Record<string, TestUser>;
