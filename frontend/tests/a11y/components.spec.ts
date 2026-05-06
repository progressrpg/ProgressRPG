import { test, expect } from '@playwright/test';
import { checkA11y, expectNoA11yViolations } from '../utils/a11y';

test.describe('Component Accessibility', () => {
  test('Button component is accessible', async ({ page }) => {
    await page.goto('/');
    await page.getByRole('heading', { name: 'Turn effort into momentum' }).waitFor();
    const results = await checkA11y(page, {
      include: ['button']
    });
    expectNoA11yViolations(results);
  });

  test('Form components are accessible', async ({ page }) => {
    await page.goto('/login');
    await page.getByRole('heading', { name: /log in/i }).waitFor();
    const results = await checkA11y(page);
    expectNoA11yViolations(results);
  });

  test('Navigation is accessible', async ({ page }) => {
    await page.goto('/');
    const results = await checkA11y(page, {
      include: ['nav', 'header']
    });
    expectNoA11yViolations(results);
  });
});

test.describe('Keyboard Navigation', () => {
  test('Can navigate buttons with keyboard', async ({ page }) => {
    await page.goto('/');
    await page.getByRole('heading', { name: 'Turn effort into momentum' }).waitFor();

    const firstButton = page.locator('button, a[role="button"]').first();
    await firstButton.focus();
    await expect(firstButton).toBeFocused();

    await page.keyboard.press('Enter');
  });

  test('Can navigate forms with keyboard', async ({ page }) => {
    await page.goto('/login');
    await page.getByRole('heading', { name: /log in/i }).waitFor();

    const emailInput = page.locator('input[type="email"]');
    await emailInput.focus();
    await expect(emailInput).toBeFocused();

    await page.keyboard.type('test@example.com');

    await page.keyboard.press('Tab');
    const passwordInput = page.locator('input[type="password"]');
    await expect(passwordInput).toBeFocused();
  });
});
