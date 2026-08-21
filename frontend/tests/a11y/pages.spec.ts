import { test } from '@playwright/test';
import { checkA11y, expectNoA11yViolations } from '../utils/a11y';
import {
  mockSuccessfulSubscriptionSync,
  stabilizeTimerPage,
  visitAuthenticatedPage,
} from '../utils/authenticatedPage';
import { timerUserStorageState } from '../../playwright/testUser';

const cleanupRoutes = async (page: Parameters<typeof test>[0]['page']) => {
  try {
    await (page as { unrouteAll?: (options?: { behavior?: 'ignoreErrors' }) => Promise<void> })
      .unrouteAll?.({ behavior: 'ignoreErrors' });
  } catch {
    // ignore cleanup errors
  }
};

test.describe('Page Accessibility', () => {
  test('Home page is accessible', async ({ page }) => {
    await page.goto('/');
    await page.getByRole('heading', { name: 'Turn effort into momentum' }).waitFor();
    const results = await checkA11y(page);
    expectNoA11yViolations(results);
  });

  test('Login page is accessible', async ({ page }) => {
    await page.goto('/login');
    await page.getByRole('heading', { name: /log in/i }).waitFor();
    const results = await checkA11y(page);
    expectNoA11yViolations(results);
  });

  test('Register page is accessible', async ({ page }) => {
    await page.goto('/register');
    // Registration is currently invite-only (self_serve_registration off),
    // so unauthenticated visitors land on the waitlist-nudge heading rather
    // than the registration form itself - see RegisterPage.tsx.
    await page.getByRole('heading', { name: /invite only|temporarily full/i }).waitFor();
    const results = await checkA11y(page);
    expectNoA11yViolations(results);
  });

  test('Privacy policy page is accessible', async ({ page }) => {
    await page.goto('/privacy-policy');
    await page.getByRole('heading', { name: 'Privacy Policy' }).waitFor();
    const results = await checkA11y(page);
    expectNoA11yViolations(results);
  });

  test('Terms of service page is accessible', async ({ page }) => {
    await page.goto('/terms-of-service');
    await page.getByRole('heading', { name: 'Terms of Service' }).waitFor();
    const results = await checkA11y(page);
    expectNoA11yViolations(results);
  });

  test('404 page should be accessible', async ({ page }) => {
    await page.goto('/nonexistent-page');
    await page.getByRole('heading', { name: /page not found/i }).waitFor();
    const results = await checkA11y(page);
    expectNoA11yViolations(results);
  });

  test('Forgot password page is accessible', async ({ page }) => {
    await page.goto('/forgot-password');
    await page
      .getByRole('heading', { name: /(forgot|reset)( your)? password/i })
      .waitFor();
    const results = await checkA11y(page);
    expectNoA11yViolations(results);
  });

  test('Support page is accessible', async ({ page }) => {
    await page.goto('/support');
    await page.getByRole('heading', { name: 'Support', exact: true }).waitFor();
    const results = await checkA11y(page);
    expectNoA11yViolations(results);
  });
});

test.describe('Authenticated Page Accessibility', () => {
  test.use({ storageState: timerUserStorageState('a11y-pages') });

  test('Timer page is accessible', async ({ page }) => {
    await stabilizeTimerPage(page);

    try {
      await page.goto('/timer');
      await page.getByRole('heading', { name: 'Timer', exact: true }).waitFor();
      const results = await checkA11y(page);
      expectNoA11yViolations(results);
    } finally {
      await cleanupRoutes(page);
    }
  });


  test('Account page is accessible', async ({ page }) => {
    await visitAuthenticatedPage(page, '/account');
    await page.getByRole('heading', { name: 'Account', exact: true }).waitFor();
    const results = await checkA11y(page);
    expectNoA11yViolations(results);
  });

  test('Tutorial modal is accessible when opened from the navbar', async ({ page }) => {
    await stabilizeTimerPage(page);

    try {
      await page.goto('/timer');
      await page.getByRole('heading', { name: 'Timer', exact: true }).waitFor();
      await page.getByRole('button', { name: 'Open tutorial' }).click();
      await page.getByRole('dialog').waitFor();
      const results = await checkA11y(page);
      expectNoA11yViolations(results);
    } finally {
      await cleanupRoutes(page);
    }
  });

  test('Upgrade page is accessible', async ({ page }) => {
    await mockSuccessfulSubscriptionSync(page);

    try {
      await visitAuthenticatedPage(page, '/upgrade');
      await page.getByRole('heading', { name: /(upgrade|premium|plan)/i }).waitFor();
      const results = await checkA11y(page);
      expectNoA11yViolations(results);
    } finally {
      await cleanupRoutes(page);
    }
  });

  test('Payment success page is accessible', async ({ page }) => {
    await mockSuccessfulSubscriptionSync(page);

    try {
      await visitAuthenticatedPage(page, '/payment-success?session_id=test-session');
      await page
        .getByRole('heading', {
          name: /(you('re| are)( now)? premium|payment success|thank(s| you))/i,
        })
        .waitFor();
      const results = await checkA11y(page);
      expectNoA11yViolations(results);
    } finally {
      await cleanupRoutes(page);
    }
  });

  test('Payment cancelled page is accessible', async ({ page }) => {
    await visitAuthenticatedPage(page, '/payment-cancelled');
    await page.getByRole('heading', { name: /payment cancelled/i }).waitFor();
    const results = await checkA11y(page);
    expectNoA11yViolations(results);
  });

  test('Edit account page is accessible', async ({ page }) => {
    await visitAuthenticatedPage(page, '/edit-account');
    await page.getByRole('heading', { name: /edit account/i }).waitFor();
    const results = await checkA11y(page);
    expectNoA11yViolations(results);
  });

  // The standalone /tasks and /activities pages were removed when both were
  // folded into the unified timer homepage (see tests/a11y/tasks.a11y.spec.ts
  // for Planning-mode/tasks coverage, and the "Timer page is accessible"
  // test above for the flag-off legacy CurrentActivity+ActivityTimeline
  // view). /projects has no route at all currently - ProjectsPanel exists
  // as a component but isn't mounted anywhere in routesConfig.jsx.
});
