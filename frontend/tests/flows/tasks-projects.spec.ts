import { expect, test } from '@playwright/test';
import { stabilizeTimerPage } from '../utils/authenticatedPage';
import { timerUserStorageState } from '../../playwright/testUser';

test.describe('Task flow', () => {
  test.use({ storageState: timerUserStorageState('tasks-projects') });

  test('can create and delete a task', async ({ page }) => {
    const taskName = `Flow test task ${Date.now()}`;

    await stabilizeTimerPage(page, { unifiedHomepage: true });

    try {
      // The standalone /tasks page was folded into Planning mode on the
      // unified timer homepage - blank start auto-labels "Planning" and
      // opens it.
      await page.goto('/timer');
      const section = page.locator('section').filter({
        has: page.getByRole('heading', { name: 'Activity timer' }),
      });
      // Start assigns and starts the activity in one atomic set_activity
      // call (start: true) - wait for that single request before touching
      // the tasks panel.
      await Promise.all([
        page.waitForResponse(
          (r) => r.url().includes('/activity_timers/set_activity/') && r.request().method() === 'POST',
        ),
        section.getByRole('button', { name: 'Start' }).click(),
      ]);
      await expect(page.getByPlaceholder('New task name')).toBeVisible();

      await page.getByPlaceholder('New task name').fill(taskName);
      const [taskPostResponse] = await Promise.all([
        page.waitForResponse(r => r.url().includes('/tasks/') && r.request().method() === 'POST'),
        page.getByRole('button', { name: /add task/i }).click(),
      ]);
      expect(taskPostResponse.status()).toBeLessThan(300);
      await page.waitForResponse(r => r.url().includes('/tasks/') && r.request().method() === 'GET');

      const taskItem = page.locator('button', { hasText: taskName });
      await expect(taskItem).toBeVisible({ timeout: 10000 });

      // Open modal and delete
      await taskItem.click();
      await page.getByRole('button', { name: 'Delete' }).click();
      await page.getByRole('button', { name: 'Delete' }).last().click(); // confirm
      await expect(taskItem).not.toBeVisible();
    } finally {
      await page.unrouteAll({ behavior: 'ignoreErrors' });
    }
  });
});

// No "Project flow" here: /projects has no route at all currently -
// ProjectsPanel exists as a component but isn't mounted anywhere in
// routesConfig.jsx, so there's no live page for this suite to cover.
