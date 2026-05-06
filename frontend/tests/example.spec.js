// example.spec.js
import { test, expect } from '@playwright/test';
import { checkA11y, expectNoA11yViolations } from './utils/a11y';

test('homepage has expected content', async ({ page }) => {
  await page.goto('/');
  await expect(page).toHaveTitle(/Progress RPG/i);
});


test('user can log in and gets redirected', async ({ page }) => {
  await page.goto('/login');

  //await page.pause();
  // Fill in email and password inputs by their name attribute
  await page.fill('input[name="email"]', 'gaidheal01+test1@gmail.com');
  await page.fill('input[name="password"]', 'correcthorsebatterystaple');

  // Click the submit button by its text (Log In)
  await page.click('button[type="submit"]');

  // Wait for navigation after successful login:
  // your app navigates either to /onboarding or /game
  // Let's wait for one of those URLs
  await page.waitForURL(/\/(onboarding|timer)/);

  // Optionally check for absence of error message
  const error = page.locator(`.${'error'}`); // your error class is from styles.error
  await expect(error).toHaveCount(0);

  // Or check that the login form is no longer visible
  await expect(page.locator('form')).toHaveCount(0);
});


test('login page is accessible', async ({ page }) => {
  await page.goto('/login');
  await page.getByRole('heading', { name: /log in/i }).waitFor();

  const results = await checkA11y(page);
  expectNoA11yViolations(results);
});
