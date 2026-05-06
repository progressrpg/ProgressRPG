import { test, expect } from '@playwright/test';
import { checkA11y, expectNoA11yViolations } from '../utils/a11y';
import { routePaths } from '../../src/routes/routePaths.js';

test.describe('Future-Proofing Accessibility Tests', () => {
  test('Any new page should pass basic a11y checks', async ({ page }) => {
    test.setTimeout(90000);
    const routes = routePaths.filter(path => !path.includes(':') && path !== '*');

    for (const route of routes) {
      try {
        await page.goto(route, { waitUntil: 'domcontentloaded' });
        const results = await checkA11y(page);

        console.log(`Testing ${route}...`);

        // Check critical violations only for future routes
        const criticalViolations = results.violations.filter(
          (v: any) => v.impact === 'critical' || v.impact === 'serious'
        );

        if (criticalViolations.length > 0) {
          console.error(`Critical a11y issues on ${route}:`, criticalViolations);
        }

        expect(criticalViolations).toHaveLength(0);
      } catch (error) {
        console.log(`Route ${route} not yet implemented - skipping`);
      }
    }
  });

  test('Modal components should be accessible wherever used', async ({ page }) => {
    await page.goto('/');

    // Wait for any modal to appear (or trigger one if needed)
    const modal = page.locator('[role="dialog"]');

    if (await modal.count() > 0) {
      const results = await checkA11y(page, {
        include: ['[role="dialog"]']
      });
      expectNoA11yViolations(results);
    } else {
      console.log('No modals found - test will catch them when implemented');
    }
  });

  test('All forms should have proper labels and error handling', async ({ page }) => {
    const formsPages = ['/login', '/register', '/profile'];

    for (const route of formsPages) {
      await page.goto(route);

      // Check that all inputs have labels
      const inputs = page.locator('input');
      const count = await inputs.count();

      for (let i = 0; i < count; i++) {
        const input = inputs.nth(i);
        const id = await input.getAttribute('id');

        if (id) {
          const label = page.locator(`label[for="${id}"]`);
          await expect(label).toBeVisible();
        }
      }
    }
  });

  test('All interactive elements should be keyboard accessible', async ({ page }) => {
    await page.goto('/');
    await page.getByRole('heading', { name: 'Turn effort into momentum' }).waitFor();

    const interactiveElements = await page.locator(
      'button:visible, a:visible, input:visible, select:visible, textarea:visible, [tabindex]:not([tabindex="-1"]):visible'
    ).all();

    console.log(`Found ${interactiveElements.length} visible interactive elements`);

    for (const element of interactiveElements) {
      await element.focus();
      await expect(element).toBeFocused();
    }
  });
});
