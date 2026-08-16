import type { Decorator } from '@storybook/react-vite';
import { AuthContext, type AuthContextValue } from '../../src/context/authContext';
import { mockAuthContextValue } from '../../src/testUtils/mockAuthContext';

/**
 * Wraps a story in `AuthContext` with a mock value, for components that read
 * `useAuth()` outside of a real session. `authenticated` controls whether the
 * mock represents a logged-in or logged-out user; `overrides` reaches any
 * other field (e.g. `user: { is_staff: true }`).
 */
export function withAuthContext(
  overrides: Partial<AuthContextValue> & { authenticated?: boolean } = {}
): Decorator {
  return (Story) => (
    <AuthContext.Provider value={mockAuthContextValue(overrides)}>
      <Story />
    </AuthContext.Provider>
  );
}
