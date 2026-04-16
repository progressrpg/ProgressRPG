import { expect, test } from '@playwright/test';
import { checkA11y, expectNoA11yViolations } from '../utils/a11y';

test.describe('Home page accessibility', () => {
  test('passes automated accessibility checks', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByRole('heading', { name: 'Turn effort into momentum' })).toBeVisible();

    const results = await checkA11y(page);
    expectNoA11yViolations(results);
  });

  test('supports screen readers and keyboard navigation', async ({ page }) => {
    await page.goto('/');

    await expect(page.getByRole('main')).toBeVisible();
    await expect(page.getByRole('link', { name: 'Skip to waitlist form' })).toHaveAttribute('href', '#signup-heading');
    await expect(page.getByRole('navigation', { name: 'Quick links' })).toBeVisible();
    await expect(page.getByRole('textbox', { name: 'Email address' })).toBeVisible();
    await expect(
      page.getByText('Only your email is required. We will use it for early-access and product updates.')
    ).toBeVisible();

    const jumpLink = page.getByRole('link', { name: 'Features' });
    await jumpLink.focus();
    await expect(jumpLink).toBeFocused();
    await page.keyboard.press('Enter');

    await expect(page).toHaveURL(/#features-heading$/);
    await expect(page.getByRole('heading', { name: 'Why Progress RPG?' })).toBeInViewport();
  });

  test('announces clear validation errors for the waitlist form', async ({ page }) => {
    await page.goto('/');

    await page.getByRole('button', { name: 'Join the waitlist' }).click();

    const alert = page.getByRole('alert');
    await expect(alert).toContainText('Enter an email address to join the waitlist.');
    await expect(page.getByRole('textbox', { name: 'Email address' })).toHaveAttribute('aria-invalid', 'true');
  });
});
