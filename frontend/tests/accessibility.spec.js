import { test } from '@playwright/test';
import { checkA11y, expectNoA11yViolations } from './utils/a11y';
import { TEST_USERS } from '../playwright/testUser';

test.describe('Authenticated accessibility', () => {
  test.use({ storageState: TEST_USERS.accessibility.storageStatePath });

  test('timer screen has no obvious accessibility violations', async ({ page }) => {
    await page.goto('/timer');
    await page.getByRole('heading', { name: 'Activity timer' }).waitFor();

    const results = await checkA11y(page);
    expectNoA11yViolations(results);
  });
});
