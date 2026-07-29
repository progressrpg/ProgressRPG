import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import OnlineCountBadgeGluestack from './OnlineCountBadge.gluestack';

vi.mock('../../context/AuthContext', () => ({
  useAuth: () => ({ isAuthenticated: true }),
}));

const mockUseOnlineCount = vi.fn(() => ({ onlinePlayerCount: 12 }));

vi.mock('../../context/OnlineCountContext', () => ({
  useOnlineCount: () => mockUseOnlineCount(),
}));

describe('OnlineCountBadge (Gluestack PoC)', () => {
  it('shows the current online player count', () => {
    mockUseOnlineCount.mockReturnValue({ onlinePlayerCount: 12 });

    render(<OnlineCountBadgeGluestack />);

    expect(screen.getByText('12 players online')).toBeInTheDocument();
  });

  it('updates displayed count from shared state', () => {
    mockUseOnlineCount.mockReturnValue({ onlinePlayerCount: 3 });

    render(<OnlineCountBadgeGluestack />);

    expect(screen.getByText('3 players online')).toBeInTheDocument();
  });
});
