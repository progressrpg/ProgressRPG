import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { TamaguiProvider } from 'tamagui';

import OnlineCountBadgeTamagui from './OnlineCountBadge.tamagui';
import tamaguiConfig from '../../../tamagui.config';

vi.mock('../../context/AuthContext', () => ({
  useAuth: () => ({ isAuthenticated: true }),
}));

const mockUseOnlineCount = vi.fn(() => ({ onlinePlayerCount: 12 }));

vi.mock('../../context/OnlineCountContext', () => ({
  useOnlineCount: () => mockUseOnlineCount(),
}));

describe('OnlineCountBadge (Tamagui PoC)', () => {
  it('shows the current online player count', () => {
    mockUseOnlineCount.mockReturnValue({ onlinePlayerCount: 12 });

    render(
      <TamaguiProvider config={tamaguiConfig}>
        <OnlineCountBadgeTamagui />
      </TamaguiProvider>
    );

    expect(screen.getByText('12 players online')).toBeInTheDocument();
  });

  it('updates displayed count from shared state', () => {
    mockUseOnlineCount.mockReturnValue({ onlinePlayerCount: 3 });

    render(
      <TamaguiProvider config={tamaguiConfig}>
        <OnlineCountBadgeTamagui />
      </TamaguiProvider>
    );

    expect(screen.getByText('3 players online')).toBeInTheDocument();
  });
});
