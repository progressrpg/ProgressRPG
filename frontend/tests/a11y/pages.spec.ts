import { test } from '@playwright/test';
import { checkA11y, expectNoA11yViolations } from '../utils/a11y';

test.describe('Page Accessibility', () => {
  test('Home page is accessible', async ({ page }) => {
    await page.goto('/');
    await page.getByRole('heading', { name: 'Turn effort into momentum' }).waitFor();
    const results = await checkA11y(page);
    expectNoA11yViolations(results);
  });

  test('Login page is accessible', async ({ page }) => {
    await page.goto('/login');
    const results = await checkA11y(page);
    expectNoA11yViolations(results);
  });

  test('Register page is accessible', async ({ page }) => {
    await page.goto('/register');
    const results = await checkA11y(page);
    expectNoA11yViolations(results);
  });

  test('Privacy policy page is accessible', async ({ page }) => {
    await page.goto('/privacy-policy');
    await page.getByRole('heading', { name: 'Privacy Policy' }).waitFor();
    const results = await checkA11y(page);
    expectNoA11yViolations(results);
  });

  test('Terms of service page is accessible', async ({ page }) => {
    await page.goto('/terms-of-service');
    await page.getByRole('heading', { name: 'Terms of Service' }).waitFor();
    const results = await checkA11y(page);
    expectNoA11yViolations(results);
  });

  // Future-proofing: Test for pages that might be added
  test('404 page should be accessible when implemented', async ({ page }) => {
    await page.goto('/nonexistent-page');
    // This will pass if you return a 200 with your standard layout
    // or if you implement a proper 404 page
    const results = await checkA11y(page);
    expectNoA11yViolations(results);
  });
});

test.describe('Authenticated Page Accessibility', () => {
  test.use({ storageState: 'playwright/.auth/user.json' });

  test('Game page is accessible', async ({ page }) => {
    await page.goto('/game');
    const results = await checkA11y(page);
    expectNoA11yViolations(results);
  });

  test('Profile page is accessible', async ({ page }) => {
    await page.goto('/profile');
    const results = await checkA11y(page);
    expectNoA11yViolations(results);
  });

  test('Onboarding page is accessible', async ({ page }) => {
    await page.goto('/onboarding');
    const results = await checkA11y(page);
    expectNoA11yViolations(results);
  });
});
