import { expect, Page, Route } from '@playwright/test';

type JsonRecord = Record<string, unknown>;

function isJsonRecord(value: unknown): value is JsonRecord {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

export async function dismissBlockingModalIfPresent(page: Page, timeout = 3000) {
  const dialogs = page.getByRole('dialog');
  const deadline = Date.now() + timeout;

  while (Date.now() < deadline) {
    const dialogCount = await dialogs.count();

    if (dialogCount === 0) {
      return;
    }

    await page.keyboard.press('Escape');

    const closeButton = page.getByRole('button', { name: 'Close modal' }).first();
    if (await closeButton.isVisible().catch(() => false)) {
      await closeButton.evaluate((button: HTMLElement) => {
        button.click();
      });
    }

    await page.waitForTimeout(100);
  }

  await expect.poll(async () => dialogs.count()).toBe(0);
}

export async function visitAuthenticatedPage(page: Page, path: string, modalTimeout = 3000) {
  await page.goto(path);
  await dismissBlockingModalIfPresent(page, modalTimeout);
}

function withSettledPlayerState(payload: unknown): unknown {
  if (!isJsonRecord(payload)) {
    return payload;
  }

  return {
    ...payload,
    onboarding_completed: true,
    unseen_tutorial_step_ids: [],
  };
}

function withSettledTimerBootstrap(payload: unknown): unknown {
  if (!isJsonRecord(payload)) {
    return payload;
  }

  const stoppedTimer = isJsonRecord(payload.activity_timer)
    ? { ...payload.activity_timer, status: 'none' }
    : payload.activity_timer;

  return {
    ...payload,
    player: isJsonRecord(payload.player)
      ? withSettledPlayerState(payload.player)
      : payload.player,
    activity_timer: stoppedTimer,
    login_state: 'none',
    loginState: 'none',
    login_event_at: null,
    loginEventAt: null,
    login_reward_xp: 0,
    loginRewardXp: 0,
    login_streak: 0,
    loginStreak: 0,
  };
}

function withStableAppConfig(payload: unknown, opts: { unifiedHomepage?: boolean } = {}): unknown {
  if (!isJsonRecord(payload)) {
    return payload;
  }

  const rawFeatureFlags = isJsonRecord(payload.feature_flags)
    ? payload.feature_flags
    : {};

  return {
    ...payload,
    stripe_live_mode:
      typeof payload.stripe_live_mode === 'boolean'
        ? payload.stripe_live_mode
        : false,
    trial_period_days:
      typeof payload.trial_period_days === 'number'
        ? payload.trial_period_days
        : 14,
    feature_flags: {
      ...rawFeatureFlags,
      tasksFeature: ['all'],
      projectsFeature: ['all'],
      categoriesFeature: ['all'],
      skillsFeature: ['all'],
      activityList: ['all'],
      unified_homepage: opts.unifiedHomepage ? ['all'] : [],
    },
  };
}

async function fulfillPatchedRoute(route: Route, patch: (payload: unknown) => unknown) {
  const response = await route.fetch();
  const payload = patch(await response.json());

  await route.fulfill({
    response,
    json: payload,
  });
}

export async function stabilizeAuthenticatedPlayer(page: Page) {
  await page.route('**/fetch_info/', async (route) => {
    await fulfillPatchedRoute(route, (payload) => {
      if (!isJsonRecord(payload)) {
        return payload;
      }

      const stoppedTimer = isJsonRecord(payload.activity_timer)
        ? { ...payload.activity_timer, status: 'none' }
        : payload.activity_timer;

      return {
        ...payload,
        player: isJsonRecord(payload.player)
          ? withSettledPlayerState(payload.player)
          : payload.player,
        activity_timer: stoppedTimer,
      };
    });
  });

  await page.route('**/me/player/', async (route) => {
    await fulfillPatchedRoute(route, withSettledPlayerState);
  });

  await page.route('**/app_config/', async (route) => {
    await fulfillPatchedRoute(route, withStableAppConfig);
  });
}

export async function stabilizeTimerPage(page: Page, opts: { unifiedHomepage?: boolean } = {}) {
  await page.route('**/fetch_info/', async (route) => {
    await fulfillPatchedRoute(route, withSettledTimerBootstrap);
  });

  await page.route('**/me/player/', async (route) => {
    await fulfillPatchedRoute(route, withSettledPlayerState);
  });

  await page.route('**/app_config/', async (route) => {
    await fulfillPatchedRoute(route, (payload) => withStableAppConfig(payload, opts));
  });
}

export async function mockSuccessfulSubscriptionSync(page: Page) {
  await page.route('**/payments/sync-subscription/', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ status: 'active' }),
    });
  });
}
