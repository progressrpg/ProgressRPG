import { expect, test } from '@playwright/test';
import { stabilizeTimerPage } from '../utils/authenticatedPage';
import { timerUserStorageState } from '../../playwright/testUser';

// Every test in this file — in both describe blocks below — drives the same
// seeded test user's single activity timer against the real backend.
// test.describe.configure({ mode: 'serial' }) only orders tests *within* the
// describe block it's called in, so a per-block serial flag here wouldn't
// stop the two blocks from being scheduled concurrently under
// fullyParallel: true. Setting it at file scope (Playwright's documented
// pattern for cross-describe ordering) forces every test in the file to run
// serially in declaration order instead.
test.describe.configure({ mode: 'serial' });

test.describe('Unified timer homepage (flag on)', () => {
  test.use({ storageState: timerUserStorageState('unified-timer-home') });

  test('blank start, label, click-to-edit, and stop happy path', async ({ page }) => {
    await stabilizeTimerPage(page, { unifiedHomepage: true });

    try {
      await page.goto('/timer');
      await expect(page.getByRole('heading', { name: 'Activity timer' })).toBeAttached();

      const section = page.locator('section').filter({
        has: page.getByRole('heading', { name: 'Activity timer' }),
      });

      // Legacy "Recent activities" feed is not rendered under the flag.
      await expect(page.getByRole('heading', { name: 'Recent activities' })).toHaveCount(0);

      // A single Start button, always enabled — starting with nothing typed
      // auto-labels the timer "Planning" and opens Planning mode.
      const startButton = section.getByRole('button', { name: 'Start' });
      await expect(startButton).toBeEnabled();
      await startButton.click();
      await expect(section.getByRole('button', { name: 'Stop' })).toBeVisible();

      const planningLabel = section.getByRole('button', { name: /Planning/ });
      await expect(planningLabel).toBeVisible();
      await expect(page.getByRole('radio', { name: 'Planning' })).toHaveAttribute('aria-checked', 'true');
      await expect(page.getByPlaceholder('New task name')).toBeVisible();

      // Click-to-edit: re-opens the input pre-filled with the current label,
      // so it can be renamed to whatever the user is actually doing.
      await planningLabel.click();
      const input = section.getByRole('combobox', { name: 'Activity name' });
      await expect(input).toHaveValue('Planning');
      await input.fill('Flow test activity');
      await input.press('Enter');

      const labelButton = section.getByRole('button', { name: /Flow test activity/ });
      await expect(labelButton).toBeVisible();
      // Scoped to the activity-name combobox specifically: Planning mode's
      // own "New task name" combobox (TasksPanel) is still on the page at
      // this point, so asserting on the whole section's combobox count would
      // wrongly fail.
      await expect(section.getByRole('combobox', { name: 'Activity name' })).toHaveCount(0);

      // Click-to-edit: re-opens the input pre-filled with the current label.
      await labelButton.click();
      const editInput = section.getByRole('combobox', { name: 'Activity name' });
      await expect(editInput).toHaveValue('Flow test activity');

      // Select-all + Backspace should actually clear the field, not silently
      // revert to the still-uncommitted original name.
      await editInput.click();
      await editInput.press('ControlOrMeta+a');
      await editInput.press('Backspace');
      await expect(editInput).toHaveValue('');
      await editInput.fill('Flow test activity');

      // Escape cancels — no request, label unchanged.
      await editInput.press('Escape');
      await expect(section.getByRole('button', { name: /Flow test activity/ })).toBeVisible();

      await section.getByRole('button', { name: 'Stop' }).click();

      // Stopping opens the activity-complete reward dialog (shared with the
      // legacy flow via useSupportFlow) — dismiss it to get back to the input state.
      await page.getByRole('button', { name: 'Back to timer' }).click();

      await expect(section.getByRole('button', { name: 'Start' })).toBeVisible();
    } finally {
      await page.unrouteAll({ behavior: 'ignoreErrors' });
    }
  });

  test('switching to Planning mode manages tasks without interfering with a running timer', async ({ page }) => {
    await stabilizeTimerPage(page, { unifiedHomepage: true });
    const taskName = `Planning mode task ${Date.now()}`;

    try {
      await page.goto('/timer');
      const section = page.locator('section').filter({
        has: page.getByRole('heading', { name: 'Activity timer' }),
      });

      // Blank start auto-labels "Planning" and opens Planning mode already —
      // no extra click needed to get there. Start assigns and starts the
      // activity in one atomic set_activity call (start: true) - wait for
      // that single request before touching the tasks panel.
      await Promise.all([
        page.waitForResponse(
          (r) => r.url().includes('/activity_timers/set_activity/') && r.request().method() === 'POST',
        ),
        section.getByRole('button', { name: 'Start' }).click(),
      ]);
      await expect(section.getByRole('button', { name: 'Stop' })).toBeVisible();
      await expect(page.getByRole('radio', { name: 'Planning' })).toHaveAttribute('aria-checked', 'true');

      // The timer stays visible/controllable while planning.
      await expect(section.getByRole('button', { name: 'Stop' })).toBeVisible();

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

      const checkbox = page.getByRole('checkbox', { name: `Mark ${taskName} as complete` });
      await expect(checkbox).toBeVisible({ timeout: 10000 });
      await Promise.all([
        page.waitForResponse(
          (r) => r.url().includes('/tasks/') && r.request().method() === 'PATCH',
        ),
        checkbox.click(),
      ]);
      await expect(
        page.getByRole('checkbox', { name: `Mark ${taskName} as complete` }),
      ).toHaveCount(0);

      // Clean up so repeated runs stay deterministic.
      await page.getByRole('button', { name: 'Show complete' }).click();
      await page.getByRole('button', { name: `Edit task ${taskName}` }).first().click();
      const dialog = page.getByRole('dialog');
      await dialog.getByRole('button', { name: 'Delete' }).click();
      await dialog.getByRole('button', { name: 'Delete' }).click();
      await expect(page.getByText(taskName)).not.toBeVisible();

      await page.getByRole('radio', { name: 'Doing' }).click();
      await expect(page.getByPlaceholder('New task name')).not.toBeVisible();

      await section.getByRole('button', { name: 'Stop' }).click();
      await page.getByRole('button', { name: 'Back to timer' }).click();
      await expect(section.getByRole('button', { name: 'Start' })).toBeVisible();
    } finally {
      await page.unrouteAll({ behavior: 'ignoreErrors' });
    }
  });

  test('the reward dialog opened from Stop is never covered by the persistent list', async ({ page }) => {
    await stabilizeTimerPage(page, { unifiedHomepage: true });

    try {
      await page.goto('/timer');
      const section = page.locator('section').filter({
        has: page.getByRole('heading', { name: 'Activity timer' }),
      });

      // Start assigns and starts the activity in one atomic set_activity
      // call (start: true) - wait for that request to resolve before
      // stopping, otherwise Stop can race the in-flight start on the
      // backend (nothing active to stop yet) and never open the reward
      // dialog.
      await Promise.all([
        page.waitForResponse(
          (r) => r.url().includes('/activity_timers/set_activity/') && r.request().method() === 'POST',
        ),
        section.getByRole('button', { name: 'Start' }).click(),
      ]);
      await section.getByRole('button', { name: 'Stop' }).click();

      const dialog = page.getByRole('dialog', { name: 'Activity complete!' });
      await expect(dialog).toBeVisible();
      // The persistent list must not paint above the modal overlay.
      await expect(dialog.getByRole('button', { name: 'Back to timer' })).toBeInViewport();
      await dialog.getByRole('button', { name: 'Back to timer' }).click();
    } finally {
      await page.unrouteAll({ behavior: 'ignoreErrors' });
    }
  });
});

test.describe('Unified timer homepage (flag off regression guard)', () => {
  test.use({ storageState: timerUserStorageState('unified-timer-home') });

  test('renders the legacy timer + activity feed unchanged', async ({ page }) => {
    await stabilizeTimerPage(page, { unifiedHomepage: false });

    try {
      await page.goto('/timer');
      await expect(page.getByRole('heading', { name: 'Activity timer' })).toBeVisible();
      await expect(page.getByRole('heading', { name: 'Recent activities' })).toBeVisible();
      // Legacy search is a transient dropdown, not a persistent list.
      await expect(page.getByRole('listbox')).toHaveCount(0);
    } finally {
      await page.unrouteAll({ behavior: 'ignoreErrors' });
    }
  });
});
