import { expect, test } from '@playwright/test';
import { visitAuthenticatedPage } from '../utils/authenticatedPage';
import { DEFAULT_USER } from '../../playwright/testUser';

/**
 * frontend/tests (the actual Playwright testDir, per playwright.config.ts)
 * had no Map or walker spec before this - Map.tsx/useMap.ts/MapPage.tsx
 * only had Vitest unit coverage. Added alongside the Map.tsx effect-hooks
 * decomposition (see .claude/plans/working-memory-load-plan.md commit 9)
 * as its regression backstop.
 *
 * Scope is deliberately minimal: one happy-path spec confirming the map
 * loads and its character layer renders without error, not a full walker
 * test suite - multi-segment paths, speed modifiers, arrival are already
 * covered server-side by locations/tests/test_movement.py. This test's job
 * is to catch "the frontend and backend movement models disagree" or
 * "Map.tsx's refactor broke rendering", not to re-prove step_toward's math
 * client-side.
 *
 * Doesn't touch /map's own e2e fixture data (whether any village/character
 * is actually seeded near the test user isn't guaranteed), so this
 * intentionally stops at "the map renders with no console/network errors"
 * rather than asserting on specific rendered features - the weaker bar the
 * audit's own open question named as the minimum worth having.
 */
test.describe('Map page', () => {
  test.use({ storageState: DEFAULT_USER.storageStatePath });

  test('loads without console or page errors', async ({ page }) => {
    const consoleErrors: string[] = [];
    const pageErrors: string[] = [];

    page.on('console', (msg) => {
      if (msg.type() === 'error') consoleErrors.push(msg.text());
    });
    page.on('pageerror', (error) => {
      pageErrors.push(error.message);
    });

    // The map feature flag defaults to ['testers'] (frontend/src/
    // featureFlags.ts) - widen it here rather than assuming the default
    // Playwright test user is in that group, following the same
    // route-interception pattern stabilizeTimerPage/stabilizeAuthenticatedPlayer
    // use for app_config elsewhere in this file's sibling helpers.
    await page.route('**/app_config/', async (route) => {
      const response = await route.fetch();
      const payload = await response.json();
      await route.fulfill({
        response,
        json: {
          ...payload,
          feature_flags: {
            ...(payload.feature_flags ?? {}),
            map: ['all'],
          },
        },
      });
    });

    await visitAuthenticatedPage(page, '/map');

    // MapLibre renders onto a <canvas> - characters/buildings aren't
    // individually-queryable DOM nodes, so this is the practical ceiling
    // for a DOM-locator assertion without reaching into the map instance.
    const canvas = page.locator('.maplibregl-canvas');
    await expect(canvas).toBeVisible();

    // Give the map a few seconds to finish loading tiles/sources/the
    // character layer and settle any walker animation frames, so a load-
    // time or animation-loop error has time to surface.
    await page.waitForTimeout(3000);

    expect(consoleErrors, `Console errors: ${consoleErrors.join('\n')}`).toEqual([]);
    expect(pageErrors, `Page errors: ${pageErrors.join('\n')}`).toEqual([]);
  });
});
