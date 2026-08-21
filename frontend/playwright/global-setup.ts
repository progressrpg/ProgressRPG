import { mkdir } from 'node:fs/promises';
import { dirname } from 'node:path';
import { chromium, type Browser } from '@playwright/test';

import { API_URL, BASE_URL, TEST_USERS, type TestUser } from './testUser';

async function seedStorageState(browser: Browser, user: TestUser): Promise<void> {
  await mkdir(dirname(user.storageStatePath), { recursive: true });

  const response = await fetch(`${API_URL}/auth/jwt/create/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: user.email, password: user.password }),
  });

  if (!response.ok) {
    throw new Error(
      [
        `Login failed for Playwright test user ${user.email}.`,
        `Run "npm run test:e2e:setup-users" from the frontend directory first.`,
        `Response: ${response.status} ${await response.text()}`,
      ].join(' '),
    );
  }

  const data = await response.json();
  const accessToken = data.access_token ?? data.access;
  const refreshToken = data.refresh_token ?? data.refresh;

  if (!accessToken || !refreshToken) {
    throw new Error(`Login response missing tokens: ${JSON.stringify(data)}`);
  }

  const context = await browser.newContext();
  const page = await context.newPage();

  await page.goto(BASE_URL);
  await page.evaluate(({ access, refresh }) => {
    localStorage.setItem(
      'authSession',
      JSON.stringify({ accessToken: access, refreshToken: refresh, persistence: 'local' }),
    );
  }, { access: accessToken, refresh: refreshToken });

  await context.storageState({ path: user.storageStatePath });
  await context.close();
}

export default async function globalSetup() {
  const browser = await chromium.launch();

  try {
    // One dedicated user per timer-touching spec file (see TEST_USERS) so
    // concurrent spec files never share an ActivityTimer/WebSocket channel.
    for (const user of Object.values(TEST_USERS)) {
      await seedStorageState(browser, user);
    }
  } finally {
    await browser.close();
  }
}
