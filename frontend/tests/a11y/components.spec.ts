import { test, expect } from '@playwright/test';
import { checkA11y, expectNoA11yViolations } from '../utils/a11y';

test.describe('Component Accessibility', () => {
  test('Button component is accessible', async ({ page }) => {
    await page.goto('/');
    const results = await checkA11y(page, {
      include: ['button']
    });
    expectNoA11yViolations(results);
  });

  test('Form components are accessible', async ({ page }) => {
    await page.goto('/login');
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
    
    // Tab through buttons
    await page.keyboard.press('Tab');
    const firstButton = await page.locator('button, a[role="button"]').first();
    await expect(firstButton).toBeFocused();
    
    // Activate with Enter
    await page.keyboard.press('Enter');
  });

  test('Can navigate forms with keyboard', async ({ page }) => {
    await page.goto('/login');
    
    // Tab to first input
    await page.keyboard.press('Tab');
    await page.keyboard.press('Tab');
    
    const emailInput = page.locator('input[type="email"]');
    await expect(emailInput).toBeFocused();
    
    // Type in input
    await page.keyboard.type('test@example.com');
    
    // Tab to next field
    await page.keyboard.press('Tab');
    const passwordInput = page.locator('input[type="password"]');
    await expect(passwordInput).toBeFocused();
  });
});
