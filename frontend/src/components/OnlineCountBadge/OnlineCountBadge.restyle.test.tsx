// PoC (Restyle): the existing OnlineCountBadge.test.tsx suite, run
// unmodified in intent against the Restyle port, per this exploration's
// established methodology (same pattern as the Tamagui/Gluestack/
// @rn-primitives PoCs). Import swapped to the Restyle version; assertions
// are identical.
import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { ThemeProvider } from '@shopify/restyle';

import OnlineCountBadgeRestyle from './OnlineCountBadge.restyle';
import restyleTheme from '../../restyle-theme';

vi.mock('../../context/AuthContext', () => ({
  useAuth: () => ({ isAuthenticated: true }),
}));

const mockUseOnlineCount = vi.fn(() => ({ onlinePlayerCount: 12 }));

vi.mock('../../context/OnlineCountContext', () => ({
  useOnlineCount: () => mockUseOnlineCount(),
}));

function renderBadge() {
  render(
    <ThemeProvider theme={restyleTheme}>
      <OnlineCountBadgeRestyle />
    </ThemeProvider>
  );
}

describe('OnlineCountBadge (Restyle PoC)', () => {
  it('shows the current online player count', () => {
    mockUseOnlineCount.mockReturnValue({ onlinePlayerCount: 12 });

    renderBadge();

    expect(screen.getByText('12 players online')).toBeInTheDocument();
  });

  it('updates displayed count from shared state', () => {
    mockUseOnlineCount.mockReturnValue({ onlinePlayerCount: 3 });

    renderBadge();

    expect(screen.getByText('3 players online')).toBeInTheDocument();
  });
});
