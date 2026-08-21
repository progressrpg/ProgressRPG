import { expect, test } from '@playwright/test';
import {
  mockSuccessfulSubscriptionSync,
  stabilizeTimerPage,
  visitAuthenticatedPage,
} from '../utils/authenticatedPage';
import { TEST_USERS } from '../../playwright/testUser';

test.describe('Public page smoke tests', () => {
  test('Home page loads', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByRole('heading', { name: 'Turn effort into momentum' })).toBeVisible();
    await expect(page.getByRole('textbox', { name: 'Email address' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Join the waitlist' })).toBeVisible();
  });

  test('Login page loads', async ({ page }) => {
    await page.goto('/login');
    await expect(page.getByRole('heading', { name: /log in/i })).toBeVisible();
    await expect(page.getByRole('textbox', { name: /email/i })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Log In', exact: true }).last()).toBeVisible();
  });

  test('Register page loads', async ({ page }) => {
    await page.goto('/register');
    // Registration is currently invite-only (self_serve_registration off),
    // so unauthenticated visitors land on the waitlist-nudge heading rather
    // than the registration form itself - see RegisterPage.tsx.
    await expect(page.getByRole('heading', { name: /invite only|temporarily full/i })).toBeVisible();
  });

  test('Forgot password page loads', async ({ page }) => {
    await page.goto('/forgot-password');
    await expect(page.getByRole('heading', { name: /(forgot|reset)( your)? password/i })).toBeVisible();
    await expect(page.getByRole('textbox', { name: /email/i })).toBeVisible();
  });

  test('Privacy policy page loads', async ({ page }) => {
    await page.goto('/privacy-policy');
    await expect(page.getByRole('heading', { name: 'Privacy Policy' })).toBeVisible();
  });

  test('Terms of service page loads', async ({ page }) => {
    await page.goto('/terms-of-service');
    await expect(page.getByRole('heading', { name: 'Terms of Service' })).toBeVisible();
  });

  test('Support page loads', async ({ page }) => {
    await page.goto('/support');
    await expect(page.getByRole('heading', { name: 'Support', exact: true })).toBeVisible();
  });

  test('404 page loads for unknown routes', async ({ page }) => {
    await page.goto('/nonexistent-page');
    await expect(page.getByRole('heading', { name: /page not found/i })).toBeVisible();
  });
});

test.describe('Authenticated page smoke tests', () => {
  test.use({ storageState: TEST_USERS['smoke-pages'].storageStatePath });

  test('Timer page loads', async ({ page }) => {
    await stabilizeTimerPage(page);

    try {
      await page.goto('/timer');
      await expect(page.getByRole('heading', { name: 'Timer', exact: true })).toBeVisible();
    } finally {
      await page.unrouteAll({ behavior: 'ignoreErrors' });
    }
  });

  test('Account page loads', async ({ page }) => {
    await visitAuthenticatedPage(page, '/account');
    await expect(page.getByRole('heading', { name: 'Account', exact: true })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Player', exact: true })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Billing', exact: true })).toBeVisible();
  });

  test('Edit account page loads', async ({ page }) => {
    await visitAuthenticatedPage(page, '/edit-account');
    await expect(page.getByRole('heading', { name: /edit account/i })).toBeVisible();
  });

  test('Upgrade page loads', async ({ page }) => {
    await visitAuthenticatedPage(page, '/upgrade');
    await expect(page.getByRole('heading', { name: /upgrade to premium/i })).toBeVisible();
    await expect(
      page.getByText(/you are already subscribed!|focused progress, unlocked\./i)
    ).toBeVisible();
  });

  test('Payment success page loads', async ({ page }) => {
    await mockSuccessfulSubscriptionSync(page);

    try {
      await visitAuthenticatedPage(page, '/payment-success?session_id=test-session');
      await expect(page.getByRole('heading', { name: /you.re premium/i })).toBeVisible();
    } finally {
      await page.unrouteAll({ behavior: 'ignoreErrors' });
    }
  });

  test('Payment cancelled page loads', async ({ page }) => {
    await visitAuthenticatedPage(page, '/payment-cancelled');
    await expect(page.getByRole('heading', { name: /payment cancelled/i })).toBeVisible();
  });

  test('Planning mode (tasks) loads from the timer page', async ({ page }) => {
    await stabilizeTimerPage(page, { unifiedHomepage: true });

    try {
      await page.goto('/timer');
      const section = page.locator('section').filter({
        has: page.getByRole('heading', { name: 'Activity timer' }),
      });

      // Blank start auto-labels "Planning" and opens Planning mode - the
      // standalone /tasks page was folded in here. Start assigns and starts
      // the activity in one atomic set_activity call (start: true) - wait
      // for that single request before touching the tasks panel.
      await Promise.all([
        page.waitForResponse(
          (r) => r.url().includes('/activity_timers/set_activity/') && r.request().method() === 'POST',
        ),
        section.getByRole('button', { name: 'Start' }).click(),
      ]);
      await expect(page.getByPlaceholder('New task name')).toBeVisible();
      await expect(page.getByRole('button', { name: /add task/i })).toBeVisible();
    } finally {
      await page.unrouteAll({ behavior: 'ignoreErrors' });
    }
  });

  // /projects has no route at all currently - ProjectsPanel exists as a
  // component but isn't mounted anywhere in routesConfig.jsx.
  //
  // /activities was also folded into the timer page: see "Timer page loads"
  // above (unified homepage) and unified-timer-home.spec.ts's flag-off
  // regression guard (legacy CurrentActivity + ActivityTimeline view).

  test('Tutorial modal opens from the navbar', async ({ page }) => {
    await stabilizeTimerPage(page);

    try {
      await page.goto('/timer');
      await expect(page.getByRole('heading', { name: 'Timer', exact: true })).toBeVisible();
      await page.getByRole('button', { name: 'Open tutorial' }).click();
      await expect(page.getByRole('dialog')).toBeVisible();
    } finally {
      await page.unrouteAll({ behavior: 'ignoreErrors' });
    }
  });
});
