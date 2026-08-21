import { expect, test } from '@playwright/test';
import { stabilizeTimerPage } from '../utils/authenticatedPage';

/**
 * End-to-end coverage for the tasks core loop (issue #469):
 * - the show/hide-complete filter and its persisted preference
 *
 * The standalone /tasks page was folded into Planning mode on the unified
 * timer homepage (TasksPanel, only reachable while a timer session is
 * active) - see UnifiedTimerHome.tsx.
 *
 * "Starts a linked activity from the task play button" is not covered here:
 * useTasksPanel.tsx's handleStartTask no-ops whenever a timer is already
 * active, but Planning mode (where the play button lives) is only reachable
 * while a timer is already active, so the button is currently dead. Needs a
 * product decision (relabel/retarget the active session vs. something else)
 * before this can be tested again.
 */

async function createTask(page: import('@playwright/test').Page, taskName: string) {
  await page.getByPlaceholder('New task name').fill(taskName);
  const [postResponse] = await Promise.all([
    page.waitForResponse(
      (r) => r.url().includes('/tasks/') && r.request().method() === 'POST',
    ),
    page.getByRole('button', { name: /add task/i }).click(),
  ]);
  expect(postResponse.status()).toBeLessThan(300);
  await page.waitForResponse(
    (r) => r.url().includes('/tasks/') && r.request().method() === 'GET',
  );
}

test.describe('Tasks core loop', () => {
  test.use({ storageState: 'playwright/.auth/user.json' });

  test('hides completed tasks and remembers the show/hide preference', async ({ page }) => {
    const taskName = `Filter task ${Date.now()}`;

    await stabilizeTimerPage(page, { unifiedHomepage: true });

    try {
      await page.goto('/timer');
      const section = page.locator('section').filter({
        has: page.getByRole('heading', { name: 'Activity timer' }),
      });

      // Blank start auto-labels "Planning" and opens Planning mode. Start
      // now assigns and starts the activity in one atomic set_activity
      // call (start: true) - wait for that single request before touching
      // the tasks panel.
      await Promise.all([
        page.waitForResponse(
          (r) => r.url().includes('/activity_timers/set_activity/') && r.request().method() === 'POST',
        ),
        section.getByRole('button', { name: 'Start' }).click(),
      ]);
      await expect(section.getByRole('button', { name: 'Stop' })).toBeVisible();
      await expect(page.getByRole('radio', { name: 'Planning' })).toHaveAttribute('aria-checked', 'true');
      await expect(page.getByPlaceholder('New task name')).toBeVisible();

      await createTask(page, taskName);

      const checkbox = page.getByRole('checkbox', { name: `Mark ${taskName} as complete` });
      await expect(checkbox).toBeVisible({ timeout: 10000 });

      // Completing the task hides it under the default "hide complete" filter.
      // Use click() rather than check() because the task disappears from the DOM
      // immediately after completion (hideCompleted=true), so Playwright can't
      // verify the checked state before the element is removed.
      await Promise.all([
        page.waitForResponse(
          (r) => r.url().includes('/tasks/') && r.request().method() === 'PATCH',
        ),
        checkbox.click(),
      ]);
      await expect(
        page.getByRole('checkbox', { name: `Mark ${taskName} as complete` }),
      ).toHaveCount(0);

      // Revealing complete tasks brings it back.
      await page.getByRole('button', { name: 'Show complete' }).click();
      await expect(page.getByText(taskName)).toBeVisible();

      // The preference survives a reload (persisted to localStorage). The
      // mock always reports activity_timer.status "none" on /fetch_info/, so
      // a reload drops back to the pre-Start screen regardless of the real
      // backend state - re-enter Planning mode to check the panel itself.
      await page.reload();
      await section.getByRole('button', { name: 'Start' }).click();
      await expect(page.getByPlaceholder('New task name')).toBeVisible();
      await expect(page.getByRole('button', { name: 'Hide complete' })).toBeVisible();
      await expect(page.getByText(taskName)).toBeVisible();

      // Clean up so repeated runs stay deterministic.
      await page.getByRole('button', { name: `Edit task ${taskName}` }).first().click();
      const dialog = page.getByRole('dialog');
      await dialog.getByRole('button', { name: 'Delete' }).click();
      await dialog.getByRole('button', { name: 'Delete' }).click();
      await expect(page.getByText(taskName)).not.toBeVisible();
    } finally {
      await page.unrouteAll({ behavior: 'ignoreErrors' });
    }
  });
});
