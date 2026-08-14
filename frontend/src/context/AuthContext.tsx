import { useCallback, useContext, useEffect, useRef, useState } from 'react';
import type { ReactElement, ReactNode } from 'react';
import { apiFetch, ApiFetchError, setUnauthorizedHandler } from "../utils/api";
import { clearAuthStorage, getStoredAuthTokens, storeAuthTokens } from '../utils/authStorage';
import { clearUserPreferences } from '../utils/userPreferences';
import { AuthContext, type AuthContextValue } from './authContext';
import type { User } from '../types';

interface ProviderProps {
  children: ReactNode;
}

// ---------------------------------------------------------------------------
// Provider
// ---------------------------------------------------------------------------

export function AuthProvider({ children }: ProviderProps): ReactElement {
  const [accessToken, setAccessToken] = useState<string | null>(() => getStoredAuthTokens().accessToken);
  const [refreshToken, setRefreshToken] = useState<string | null>(() => getStoredAuthTokens().refreshToken);
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  const isAuthenticated = user !== null;

  // Set by login() right before it updates accessToken/refreshToken, so the
  // verifyUser effect below (which reacts to those same tokens) can tell
  // "tokens just changed because login() already fetched /me/ itself" apart
  // from "tokens changed for some other reason and still need verifying" —
  // without this, every login fires the /me/ request twice.
  const justLoggedInRef = useRef(false);

  // Thin wrapper around apiFetch. Typed as a generic fn rather than `typeof apiFetch`
  // because the overloaded signature doesn't unify to a single assignable type.
  const authFetch = <T = unknown>(path: string, options?: Parameters<typeof apiFetch>[1]): Promise<T> => {
    return apiFetch<T>(path, options);
  };

  const logout = useCallback((): void => {
    clearAuthStorage();
    clearUserPreferences();
    setAccessToken(null);
    setRefreshToken(null);
    setUser(null);
  }, []);

  useEffect(() => {
    // api.ts is a plain module with no direct line into React state, so it
    // can't call logout() itself — it invokes whatever's registered here
    // instead of broadcasting a DOM CustomEvent.
    setUnauthorizedHandler(logout);
    return () => setUnauthorizedHandler(null);
  }, [logout]);

  // Fetches the current user and applies it to state. Shared by the
  // initial-load/token-change verification below and by login(), so there's
  // one "did this session actually resolve to a user" path instead of two
  // that can drift apart.
  const loadCurrentUser = useCallback(async (onFailure: () => void): Promise<User | null> => {
    try {
      const data = await apiFetch<User>('/me/');
      setUser(data);
      return data;
    } catch (err) {
      // A 401 already ran the registered unauthorized handler (logout) from
      // inside apiFetch — calling onFailure again here is a harmless no-op
      // in that case. A service-unavailable/network error is not evidence
      // the session itself is invalid (apiFetch is already navigating away
      // for those), so don't treat it as one.
      if (err instanceof ApiFetchError && err.kind !== "unauthorized") {
        return null;
      }
      onFailure();
      return null;
    }
  }, []);

  useEffect(() => {
    async function verifyUser(): Promise<void> {
      if (justLoggedInRef.current) {
        justLoggedInRef.current = false;
        return;
      }

      if (!accessToken || !refreshToken) {
        setLoading(false);
        return;
      }

      setLoading(true);
      await loadCurrentUser(logout);
      setLoading(false);
    }

    verifyUser();
  }, [accessToken, refreshToken, loadCurrentUser, logout]);

  const login = async (
    accessToken: string,
    refreshToken: string,
    options: { rememberMe?: boolean } = {}
  ): Promise<unknown> => {
    const { rememberMe = false } = options;
    storeAuthTokens(accessToken, refreshToken, rememberMe);
    justLoggedInRef.current = true;
    setAccessToken(accessToken);
    setRefreshToken(refreshToken);
    setLoading(true);

    const data = await loadCurrentUser(() => setUser(null));
    setLoading(false);
    return data;
  };

  const value: AuthContextValue = {
    accessToken,
    refreshToken,
    isAuthenticated,
    user,
    setUser,
    login,
    logout,
    authFetch,
    loading,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return ctx;
}
