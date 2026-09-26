import { describe, expect, it } from 'vitest';

import { API_BASE_URL, resolveApiBaseUrl } from './config';

// resolveApiBaseUrl reads import.meta.env by default, but takes an override so
// the unconfigured/misconfigured cases are testable: vi.stubEnv can set a value
// but not remove one, and .env.test supplies a real value to the whole suite.
const env = (value?: string) => ({ VITE_API_BASE_URL: value }) as unknown as ImportMetaEnv;

describe('resolveApiBaseUrl', () => {
  it('uses the configured value', () => {
    expect(resolveApiBaseUrl(env('https://web-staging-wjii.onrender.com'))).toBe(
      'https://web-staging-wjii.onrender.com',
    );
  });

  it('trims a configured API base URL before use', () => {
    expect(resolveApiBaseUrl(env(' https://web-staging-wjii.onrender.com/ '))).toBe(
      'https://web-staging-wjii.onrender.com',
    );
  });

  it('strips a trailing /api/v1 suffix, with or without a trailing slash', () => {
    expect(resolveApiBaseUrl(env('https://example.com/api/v1'))).toBe('https://example.com');
    expect(resolveApiBaseUrl(env('https://example.com/api/v1/'))).toBe('https://example.com');
  });

  it('throws when the env value is missing', () => {
    expect(() => resolveApiBaseUrl(env())).toThrow(/VITE_API_BASE_URL is not set/);
  });

  it('throws when the env value is blank', () => {
    expect(() => resolveApiBaseUrl(env('   '))).toThrow(/VITE_API_BASE_URL is not set/);
  });

  it('does not consult window.location', () => {
    // The point of #571: no origin sniffing. Guard against it regressing by
    // resolving under a hostname that would previously have changed the answer.
    window.history.pushState({}, '', 'http://localhost:3000/');
    expect(resolveApiBaseUrl(env('https://api.example.com'))).toBe('https://api.example.com');
  });
});

describe('API_BASE_URL', () => {
  it('resolves from .env.test for the suite', () => {
    expect(API_BASE_URL).toBe('http://localhost:8000');
  });
});
