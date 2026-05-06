import { test } from '@playwright/test';
import { checkA11y, expectNoA11yViolations } from './utils/a11y';


test.skip('game screen has no obvious accessibility violations', async ({ page }) => {
  await page.goto('/login');
  await page.fill('input[name="email"]', 'gaidheal01+test1@gmail.com');
  await page.fill('input[name="password"]', 'correcthorsebatterystaple');
  const form = page.locator('form');
  await form.getByRole('button', { name: 'Log In' }).click();

  await page.waitForURL('**/game', { timeout: 10000 });

  const results = await checkA11y(page);
  expectNoA11yViolations(results);
});
