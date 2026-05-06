import { chromium } from '@playwright/test';

const BASE_URL = 'http://localhost:5173';
const API_URL = 'http://localhost:8000/api/v1';
const TEST_EMAIL = 'gaidheal01+test1@gmail.com';
const TEST_PASSWORD = 'correcthorsebatterystaple';

export default async function globalSetup() {
  const response = await fetch(`${API_URL}/auth/jwt/create/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: TEST_EMAIL, password: TEST_PASSWORD }),
  });

  if (!response.ok) {
    throw new Error(`Login failed: ${response.status} ${await response.text()}`);
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
    localStorage.setItem('accessToken', access);
    localStorage.setItem('refreshToken', refresh);
  }, { access: accessToken, refresh: refreshToken });

  await context.storageState({ path: 'playwright/.auth/user.json' });
  await browser.close();
}
