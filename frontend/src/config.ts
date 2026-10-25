// src/config.ts

/**
 * Base URL for the Django backend, as an absolute origin (no trailing slash,
 * no `/api/v1` suffix - callers append their own paths).
 *
 * This is configured explicitly per environment via `VITE_API_BASE_URL`, never
 * inferred from the page that happens to be serving the app:
 *
 * - local dev / `--mode development` builds: `.env.development`
 * - vitest (`--mode test`): `.env.test`
 * - Storybook's static build: a placeholder injected in `.storybook/main.ts`
 * - staging / production: the Render env var on the `frontend` service
 *   (`render.yaml` / `render-staging.yaml`, `sync: false`)
 *
 * Inferring it used to mean falling back to `window.location.origin`, which is
 * (a) unavailable on React Native, where there is no page origin to sniff
 * (#569/#571), and (b) wrong in every deployed environment anyway: the
 * frontend is a Render static site on its own hostname, so its origin is not
 * the backend's. That fallback only ever looked harmless because
 * `VITE_API_BASE_URL` is in fact always set in staging and production - if it
 * were dropped, it would have silently pointed the whole app at the static
 * site instead of failing. Hence the throw below rather than a guess.
 */
const API_BASE_URL_ENV_VAR = 'VITE_API_BASE_URL';

/**
 * Strip a `/api/v1` suffix and any trailing slash, so a value configured as
 * either an origin or a full API root resolves to the same base. Callers
 * concatenate `/api/v1/...` themselves.
 */
function normaliseApiBaseUrl(value: string): string {
  return value.replace(/\/api\/v1\/?$/i, '').replace(/\/$/, '');
}

export function resolveApiBaseUrl(
  env: ImportMetaEnv = import.meta.env,
): string {
  const rawEnvApiBaseUrl = env[API_BASE_URL_ENV_VAR] as string | undefined;
  const configured =
    typeof rawEnvApiBaseUrl === 'string' ? rawEnvApiBaseUrl.trim() : '';

  if (configured.length === 0) {
    throw new Error(
      `${API_BASE_URL_ENV_VAR} is not set. The API base URL must be configured ` +
        'explicitly for every environment - it is no longer inferred from ' +
        'window.location. Set it in the environment (Render env var for ' +
        'staging/production) or in the matching frontend/.env.<mode> file.',
    );
  }

  return normaliseApiBaseUrl(configured);
}

export const API_BASE_URL = resolveApiBaseUrl();
