import { beforeEach, describe, expect, it } from 'vitest';

import {
  clearAuthStorage,
  getStoredAccessToken,
  getStoredAuthTokens,
  storeAuthTokens,
  updateStoredAccessToken,
} from './authStorage';

describe('authStorage', () => {
  beforeEach(() => {
    localStorage.clear();
    sessionStorage.clear();
  });

  it('stores remembered tokens in localStorage', () => {
    storeAuthTokens('access-token', 'refresh-token', true);

    expect(localStorage.getItem('accessToken')).toBe('access-token');
    expect(localStorage.getItem('refreshToken')).toBe('refresh-token');
    expect(sessionStorage.getItem('accessToken')).toBeNull();
    expect(sessionStorage.getItem('refreshToken')).toBeNull();
  });

  it('stores short-session tokens in sessionStorage', () => {
    storeAuthTokens('access-token', 'refresh-token', false);

    expect(sessionStorage.getItem('accessToken')).toBe('access-token');
    expect(sessionStorage.getItem('refreshToken')).toBe('refresh-token');
    expect(localStorage.getItem('accessToken')).toBeNull();
    expect(localStorage.getItem('refreshToken')).toBeNull();
  });

  it('reads tokens from whichever auth storage is active', () => {
    sessionStorage.setItem('accessToken', 'session-access');
    sessionStorage.setItem('refreshToken', 'session-refresh');

    expect(getStoredAuthTokens()).toEqual({
      accessToken: 'session-access',
      refreshToken: 'session-refresh',
    });
    expect(getStoredAccessToken()).toBe('session-access');
  });

  it('updates refreshed access tokens in the active storage', () => {
    storeAuthTokens('old-access', 'refresh-token', false);

    updateStoredAccessToken('new-access');

    expect(sessionStorage.getItem('accessToken')).toBe('new-access');
    expect(localStorage.getItem('accessToken')).toBeNull();
  });

  it('clears auth tokens from both storages', () => {
    localStorage.setItem('accessToken', 'local-access');
    localStorage.setItem('refreshToken', 'local-refresh');
    sessionStorage.setItem('accessToken', 'session-access');
    sessionStorage.setItem('refreshToken', 'session-refresh');

    clearAuthStorage();

    expect(getStoredAuthTokens()).toEqual({
      accessToken: null,
      refreshToken: null,
    });
  });
});
