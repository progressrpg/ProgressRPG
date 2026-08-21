import { afterEach, describe, expect, it, vi } from 'vitest';

import { resolveApiBaseUrl } from './config';

describe('resolveApiBaseUrl', () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    window.history.pushState({}, '', 'http://localhost:3000/');
  });

  it('falls back to localhost when the env value is blank', () => {
    vi.stubEnv('VITE_API_BASE_URL', '   ');

    expect(resolveApiBaseUrl()).toBe('http://localhost:8000');
  });

  it('trims a configured API base URL before use', () => {
    vi.stubEnv('VITE_API_BASE_URL', ' https://web-staging-wjii.onrender.com/ ');

    expect(resolveApiBaseUrl()).toBe('https://web-staging-wjii.onrender.com');
  });
});
