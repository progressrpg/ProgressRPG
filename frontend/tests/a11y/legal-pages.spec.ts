import { expect, test } from '@playwright/test';

test.describe('Legal page navigation accessibility', () => {
  test('privacy policy TOC and top button are keyboard accessible', async ({ page }) => {
    await page.goto('/privacy-policy');

    const tocLink = page.getByRole('link', { name: '7. Your Rights' });
    await tocLink.focus();
    await expect(tocLink).toBeFocused();
    await page.keyboard.press('Enter');

    await expect(page).toHaveURL(/#7-your-rights$/);
    await expect(page.getByRole('heading', { name: '7. Your Rights' })).toBeInViewport();

    const topButton = page.getByRole('button', { name: 'Back to top' });
    await topButton.focus();
    await expect(topButton).toBeFocused();
  });

  test('terms page TOC and policy link are announced clearly', async ({ page }) => {
    await page.goto('/terms-of-service');

    await expect(page.getByRole('main')).toBeVisible();
    await expect(page.getByRole('navigation', { name: 'Contents' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Privacy Policy' }).first()).toBeVisible();
    await expect(page.getByRole('button', { name: 'Back to top' })).toBeVisible();
  });
});
