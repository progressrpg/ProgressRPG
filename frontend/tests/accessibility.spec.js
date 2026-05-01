import { test } from '@playwright/test';
import { injectAxe, checkA11y } from 'axe-playwright';


test.skip('game screen has no obvious accessibility violations', async ({ page }) => {
  // First, go to the login page and log in
  await page.goto('http://localhost:5173/login');
  await page.fill('input[name="email"]', 'gaidheal01+test1@gmail.com');
  await page.fill('input[name="password"]', 'correcthorsebatterystaple');
  const form = page.locator('form');
  await form.getByRole('button', { name: 'Log In' }).click();

  // Wait for redirection to game screen (adjust if onboarding comes first)
  await page.waitForURL('**/game', { timeout: 10000 });

  // Inject axe-core and run accessibility scan
  await injectAxe(page);
  await checkA11y(page, null, {
    detailedReport: true,
    detailedReportOptions: { html: true },
  });
});
