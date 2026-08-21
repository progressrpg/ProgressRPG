import { test, expect } from '@playwright/test';
import { checkA11y, expectNoA11yViolations } from '../utils/a11y';
import { stabilizeTimerPage } from '../utils/authenticatedPage';
import { TEST_USERS } from '../../playwright/testUser';

/**
 * Accessibility coverage for the tasks core loop (issue #469): the tasks
 * panel, its add-task autocomplete input, and the task edit dialog.
 *
 * The standalone `/tasks` page was removed when tasks were folded into the
 * unified timer homepage's Planning mode (TasksPanel, only reachable while
 * a timer session is active) - see UnifiedTimerHome.tsx.
 */

test.describe('Tasks page accessibility', () => {
  test.use({ storageState: TEST_USERS['a11y-tasks'].storageStatePath });

  test('tasks panel and add-task input have no detectable violations', async ({ page }) => {
    await stabilizeTimerPage(page, { unifiedHomepage: true });
    await page.goto('/timer');
    const section = page.locator('section').filter({
      has: page.getByRole('heading', { name: 'Activity timer' }),
    });

    // Blank start auto-labels "Planning" and opens Planning mode. Start
    // assigns and starts the activity in one atomic set_activity call
    // (start: true) - wait for that single request before touching the
    // tasks panel.
    await Promise.all([
      page.waitForResponse(
        (r) => r.url().includes('/activity_timers/set_activity/') && r.request().method() === 'POST',
      ),
      section.getByRole('button', { name: 'Start' }).click(),
    ]);
    await expect(page.getByPlaceholder('New task name')).toBeVisible();

    // The timer pill, activity label, and search control fade in over 180ms
    // (UnifiedTimerHome.tsx's fadeTransition) - wait for that to settle so
    // axe doesn't sample a low-opacity mid-fade frame as a false-positive
    // contrast violation.
    await page.waitForTimeout(300);

    const results = await checkA11y(page);
    expectNoA11yViolations(results);
  });

  test('task edit dialog is accessible', async ({ page }) => {
    const taskName = `A11y task ${Date.now()}`;

    await stabilizeTimerPage(page, { unifiedHomepage: true });
    await page.goto('/timer');
    const section = page.locator('section').filter({
      has: page.getByRole('heading', { name: 'Activity timer' }),
    });

    // Start assigns and starts the activity in one atomic set_activity call
    // (start: true) - wait for that single request before touching the
    // tasks panel.
    await Promise.all([
      page.waitForResponse(
        (r) => r.url().includes('/activity_timers/set_activity/') && r.request().method() === 'POST',
      ),
      section.getByRole('button', { name: 'Start' }).click(),
    ]);
    await expect(page.getByPlaceholder('New task name')).toBeVisible();

    await page.getByPlaceholder('New task name').fill(taskName);
    await Promise.all([
      page.waitForResponse(
        (r) => r.url().includes('/tasks/') && r.request().method() === 'POST',
      ),
      page.getByRole('button', { name: /add task/i }).click(),
    ]);
    await page.waitForResponse(
      (r) => r.url().includes('/tasks/') && r.request().method() === 'GET',
    );

    await page.getByRole('button', { name: `Edit task ${taskName}` }).first().click();
    const dialog = page.getByRole('dialog');
    await expect(dialog).toBeVisible();

    const results = await checkA11y(page, { include: ['[role="dialog"]'] });
    expectNoA11yViolations(results);

    // Clean up the task created for this scan.
    await dialog.getByRole('button', { name: 'Delete' }).click();
    await dialog.getByRole('button', { name: 'Delete' }).click();
  });
});
