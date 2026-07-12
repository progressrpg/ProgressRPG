import { expect, test } from '@playwright/test';
import { stabilizeTimerPage } from '../utils/authenticatedPage';

test.describe('Unified timer homepage (flag on)', () => {
  test.use({ storageState: 'playwright/.auth/user.json' });
  // Both tests below drive the same seeded test user's single activity timer
  // against the real backend — running them concurrently races Start/Stop
  // calls against each other, so force this suite to run serially.
  test.describe.configure({ mode: 'serial' });

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

      // A single Start button, always enabled — starts blank when the input is empty.
      const startButton = section.getByRole('button', { name: 'Start' });
      await expect(startButton).toBeEnabled();
      await startButton.click();
      await expect(section.getByRole('button', { name: 'Stop' })).toBeVisible();

      const input = section.getByRole('combobox', { name: 'Activity name' });
      await expect(input).toBeVisible();
      await input.fill('Flow test activity');
      await input.press('Enter');

      const labelButton = section.getByRole('button', { name: /Flow test activity/ });
      await expect(labelButton).toBeVisible();
      await expect(section.getByRole('combobox')).toHaveCount(0);

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

      await section.getByRole('button', { name: 'Start' }).click();
      await expect(section.getByRole('button', { name: 'Stop' })).toBeVisible();

      await page.getByRole('radio', { name: 'Planning' }).click();

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

      await section.getByRole('button', { name: 'Start' }).click();
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
  test.use({ storageState: 'playwright/.auth/user.json' });

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
