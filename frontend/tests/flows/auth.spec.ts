import { expect, test } from '@playwright/test';

import { TEST_EMAIL, TEST_PASSWORD, TEST_USERS } from '../../playwright/testUser';

test.describe('Login flow', () => {
  test('valid credentials redirect to timer or onboarding', async ({ page }) => {
    await page.goto('/login');
    await page.fill('#email', TEST_EMAIL);
    await page.fill('#password', TEST_PASSWORD);
    await page.getByRole('button', { name: 'Log In', exact: true }).click();
    await page.waitForURL(/\/(timer|onboarding)/);
  });

  test('invalid credentials show error message', async ({ page }) => {
    await page.goto('/login');
    await page.fill('#email', TEST_EMAIL);
    await page.fill('#password', 'wrongpassword');
    await page.getByRole('button', { name: 'Log In', exact: true }).click();
    await expect(page.getByRole('alert')).toBeVisible();
    await expect(page).toHaveURL(/\/login/);
  });
});

test.describe('Logout flow', () => {
  test.use({ storageState: TEST_USERS['auth-logout'].storageStatePath });

  test('logout redirects to home and clears session', async ({ page }) => {
    await page.goto('/logout');
    await expect(page.getByRole('heading', { name: /logging you out/i })).toBeVisible();
    await page.waitForURL('/');
    // Verify no longer authenticated — /timer should redirect away
    await page.goto('/timer');
    await page.waitForURL(/\/login/);
  });
});
