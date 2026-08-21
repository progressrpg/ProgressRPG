import { beforeEach, describe, expect, it } from 'vitest';

import {
  clearAuthStorage,
  getStoredAccessToken,
  getStoredAuthTokens,
  storeAuthTokens,
  updateStoredAccessToken,
} from './authStorage';

const AUTH_SESSION_KEY = 'authSession';

function readDescriptor(storage: Storage): { accessToken: string; refreshToken: string; persistence: string } | null {
  const raw = storage.getItem(AUTH_SESSION_KEY);
  return raw ? JSON.parse(raw) : null;
}

describe('authStorage', () => {
  beforeEach(() => {
    localStorage.clear();
    sessionStorage.clear();
  });

  it('stores remembered tokens in localStorage', () => {
    storeAuthTokens('access-token', 'refresh-token', true);

    expect(readDescriptor(localStorage)).toEqual({
      accessToken: 'access-token',
      refreshToken: 'refresh-token',
      persistence: 'local',
    });
    expect(sessionStorage.getItem(AUTH_SESSION_KEY)).toBeNull();
  });

  it('stores short-session tokens in sessionStorage', () => {
    storeAuthTokens('access-token', 'refresh-token', false);

    expect(readDescriptor(sessionStorage)).toEqual({
      accessToken: 'access-token',
      refreshToken: 'refresh-token',
      persistence: 'session',
    });
    expect(localStorage.getItem(AUTH_SESSION_KEY)).toBeNull();
  });

  it('reads tokens from whichever auth storage is active', () => {
    storeAuthTokens('session-access', 'session-refresh', false);

    expect(getStoredAuthTokens()).toEqual({
      accessToken: 'session-access',
      refreshToken: 'session-refresh',
    });
    expect(getStoredAccessToken()).toBe('session-access');
  });

  it('does not clobber an existing remembered session when storing a short session', () => {
    // Simulates another tab having a remembered (localStorage) session active.
    storeAuthTokens('other-tab-access', 'other-tab-refresh', true);

    storeAuthTokens('this-tab-access', 'this-tab-refresh', false);

    // The other tab's remembered tokens must survive.
    expect(readDescriptor(localStorage)).toEqual({
      accessToken: 'other-tab-access',
      refreshToken: 'other-tab-refresh',
      persistence: 'local',
    });
    // But this tab must read back its own short-session tokens, not the
    // remembered ones sitting in localStorage.
    expect(getStoredAuthTokens()).toEqual({
      accessToken: 'this-tab-access',
      refreshToken: 'this-tab-refresh',
    });
  });

  it('updates refreshed access tokens in the active storage', () => {
    storeAuthTokens('old-access', 'refresh-token', false);

    updateStoredAccessToken('new-access');

    expect(readDescriptor(sessionStorage)?.accessToken).toBe('new-access');
    expect(localStorage.getItem(AUTH_SESSION_KEY)).toBeNull();
  });

  it('treats corrupted JSON in the active storage as no session', () => {
    localStorage.setItem(AUTH_SESSION_KEY, 'not-json{');

    expect(getStoredAuthTokens()).toEqual({ accessToken: null, refreshToken: null });
  });

  it('treats a descriptor missing a token as no session', () => {
    localStorage.setItem(AUTH_SESSION_KEY, JSON.stringify({ accessToken: 'only-access' }));

    expect(getStoredAuthTokens()).toEqual({ accessToken: null, refreshToken: null });
  });

  it('updates a remembered (localStorage) session with no sessionStorage descriptor', () => {
    storeAuthTokens('old-access', 'refresh-token', true);

    updateStoredAccessToken('new-access');

    expect(readDescriptor(localStorage)?.accessToken).toBe('new-access');
  });

  it('is a no-op when neither storage has a descriptor to update', () => {
    expect(() => updateStoredAccessToken('new-access')).not.toThrow();
    expect(readDescriptor(localStorage)).toBeNull();
    expect(readDescriptor(sessionStorage)).toBeNull();
  });

  it('updates the access token in sessionStorage rather than a stale localStorage bundle', () => {
    storeAuthTokens('other-tab-access', 'other-tab-refresh', true);
    storeAuthTokens('this-tab-access', 'this-tab-refresh', false);

    updateStoredAccessToken('refreshed-access');

    expect(readDescriptor(sessionStorage)?.accessToken).toBe('refreshed-access');
    expect(readDescriptor(localStorage)?.accessToken).toBe('other-tab-access');
  });

  it('clears a remembered session from localStorage without touching another tab session', () => {
    storeAuthTokens('local-access', 'local-refresh', true);

    clearAuthStorage();

    expect(localStorage.getItem(AUTH_SESSION_KEY)).toBeNull();
  });

  it('clears a session-scoped login from sessionStorage without clobbering another tab\'s remembered session', () => {
    // Simulates another tab having a remembered (localStorage) session active.
    storeAuthTokens('other-tab-access', 'other-tab-refresh', true);
    storeAuthTokens('this-tab-access', 'this-tab-refresh', false);

    clearAuthStorage();

    expect(sessionStorage.getItem(AUTH_SESSION_KEY)).toBeNull();
    // The other tab's remembered tokens must survive a same-tab logout.
    expect(readDescriptor(localStorage)).toEqual({
      accessToken: 'other-tab-access',
      refreshToken: 'other-tab-refresh',
      persistence: 'local',
    });
  });
});
