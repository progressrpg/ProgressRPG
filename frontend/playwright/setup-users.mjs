#!/usr/bin/env node
// Seeds every dedicated Playwright test user (see ./testUser.ts's TEST_USERS).
// Kept in plain JS rather than importing testUser.ts directly since the repo
// has no TS runner wired up for standalone scripts — the slug list here must
// stay in sync with the keys of TEST_USERS.
import { spawnSync } from 'node:child_process';

const EMAIL = process.env.PLAYWRIGHT_TEST_EMAIL ?? 'playwright@example.com';
const PASSWORD = process.env.PLAYWRIGHT_TEST_PASSWORD ?? 'correcthorsebatterystaple';
const [EMAIL_LOCAL, EMAIL_DOMAIN] = EMAIL.split('@');

// One dedicated user per timer-touching spec file - keep in sync with
// TEST_USERS in ./testUser.ts (everything except 'default').
const SLUGS = [
  'a11y-pages',
  'a11y-tasks',
  'accessibility',
  'auth-logout',
  'tasks-core-loop',
  'tasks-projects',
  'timer',
  'unified-timer-home',
  'smoke-pages',
];

const users = [
  { email: EMAIL, playerName: 'Playwright Hero' },
  ...SLUGS.map((slug) => ({
    email: `${EMAIL_LOCAL}+${slug}@${EMAIL_DOMAIN}`,
    playerName: `Playwright ${slug}`,
  })),
];

for (const user of users) {
  console.log(`Seeding ${user.email}...`);
  const result = spawnSync(
    'docker',
    [
      'compose', '-f', '../compose.yaml', 'run', '--rm', 'web',
      'python', 'manage.py', 'seed_playwright_user',
      '--email', user.email,
      '--password', PASSWORD,
      '--player-name', user.playerName,
    ],
    { stdio: 'inherit' },
  );

  if (result.status !== 0) {
    console.error(`Failed to seed ${user.email}`);
    process.exit(result.status ?? 1);
  }
}
