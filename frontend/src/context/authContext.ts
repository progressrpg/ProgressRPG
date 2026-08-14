import { createContext } from 'react';
import type { Dispatch, SetStateAction } from 'react';
import type { apiFetch } from '../utils/api';
import type { User } from '../types';

export interface AuthContextValue {
  accessToken: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  user: User | null;
  setUser: Dispatch<SetStateAction<User | null>>;
  login: (accessToken: string, refreshToken: string, options?: { rememberMe?: boolean }) => Promise<unknown>;
  logout: () => void;
  /** Thin wrapper around apiFetch — use apiFetch directly for typed responses. */
  authFetch: <T = unknown>(path: string, options?: Parameters<typeof apiFetch>[1]) => Promise<T>;
  loading: boolean;
}

export const AuthContext = createContext<AuthContextValue | null>(null);
