import { mkdir } from 'node:fs/promises';
import { dirname } from 'node:path';
import { chromium } from '@playwright/test';

import {
  API_URL,
  BASE_URL,
  TEST_EMAIL,
  TEST_PASSWORD,
  TEST_USER_STORAGE_STATE_PATH,
} from './testUser';

export default async function globalSetup() {
  await mkdir(dirname(TEST_USER_STORAGE_STATE_PATH), { recursive: true });

  const response = await fetch(`${API_URL}/auth/jwt/create/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: TEST_EMAIL, password: TEST_PASSWORD }),
  });

  if (!response.ok) {
    throw new Error(
      [
        `Login failed for Playwright test user ${TEST_EMAIL}.`,
        `Run "npm run test:e2e:setup-user" from the frontend directory first.`,
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

  const browser = await chromium.launch();
  const context = await browser.newContext();
  const page = await context.newPage();

  await page.goto(BASE_URL);
  await page.evaluate(({ access, refresh }) => {
    localStorage.setItem(
      'authSession',
      JSON.stringify({ accessToken: access, refreshToken: refresh, persistence: 'local' }),
    );
  }, { access: accessToken, refresh: refreshToken });

  await context.storageState({ path: TEST_USER_STORAGE_STATE_PATH });
  await browser.close();
}
