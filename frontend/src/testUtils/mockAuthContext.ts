import type { AuthContextValue } from '../context/authContext';
import type { User } from '../types';

const mockUser: User = {
  email: 'demo@example.com',
  is_confirmed: true,
  is_staff: false,
  is_superuser: false,
  date_of_birth: null,
  timezone: 'UTC',
};

/**
 * Minimal `AuthContextValue` for Storybook stories that read `useAuth()`
 * directly (`Navbar`, `NavDrawer`, `Footer`). `authenticated: false` (the
 * default) mirrors the real logged-out render - `AuthProvider` itself never
 * calls the API when there are no stored tokens, so it doesn't need a mock.
 * `authenticated: true` covers the logged-in nav state without a real
 * session. Pass `overrides` for anything else (e.g. `user: { is_staff: true }`).
 */
export function mockAuthContextValue(
  overrides: Partial<AuthContextValue> & { authenticated?: boolean } = {}
): AuthContextValue {
  const { authenticated = false, ...rest } = overrides;

  return {
    accessToken: authenticated ? 'mock-access-token' : null,
    refreshToken: authenticated ? 'mock-refresh-token' : null,
    isAuthenticated: authenticated,
    user: authenticated ? mockUser : null,
    setUser: () => {},
    login: async () => null,
    logout: () => {},
    authFetch: async () => {
      throw new Error('authFetch is not mocked in Storybook');
    },
    loading: false,
    ...rest,
  };
}
