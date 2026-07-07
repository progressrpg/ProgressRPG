import { expect, test } from '@playwright/test';
import {
  stabilizeTimerPage,
} from '../utils/authenticatedPage';

test.describe('Timer flow', () => {
  test.use({ storageState: 'playwright/.auth/user.json' });

  test('can start and stop an activity', async ({ page }) => {
    await stabilizeTimerPage(page);

    try {
      await page.goto('/timer');
      await expect(page.getByRole('heading', { name: 'Activity timer' })).toBeVisible();

      const timerSection = page.locator('section').filter({
        has: page.getByRole('heading', { name: 'Activity timer' }),
      });
      const activityInput = timerSection.getByPlaceholder(/start typing/i);
      await activityInput.fill('Flow test activity');

      await timerSection.getByRole('button', { name: 'Start' }).click();
      await expect(timerSection.getByRole('button', { name: 'Stop' })).toBeVisible();

      await timerSection.getByRole('button', { name: 'Stop' }).click();
      await expect(timerSection.getByRole('button', { name: 'Start' })).toBeVisible();
    } finally {
      await page.unrouteAll({ behavior: 'ignoreErrors' });
    }
  });
});
