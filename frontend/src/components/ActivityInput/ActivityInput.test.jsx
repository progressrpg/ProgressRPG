import { render, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import ActivityInput from './ActivityInput';

const mockUseGame = vi.fn();
const mockUseSupportFlow = vi.fn();
const openActivityReward = vi.fn();
const fetchCharacterCurrent = vi.fn();
const fetchActivities = vi.fn();
const clearAutoStopCompletion = vi.fn();

vi.mock('../../context/GameContext', () => ({
  useGame: () => mockUseGame(),
}));

vi.mock('../../hooks/useSupportFlow', () => ({
  useSupportFlow: (...args) => mockUseSupportFlow(...args),
}));

vi.mock('../SupportFlow/SupportFlowModal', () => ({
  default: () => null,
}));

vi.mock('../../utils/sounds', () => ({
  playLimitReachedSound: vi.fn(),
}));

describe('ActivityInput', () => {
  beforeEach(() => {
    openActivityReward.mockReset();
    fetchCharacterCurrent.mockReset();
    fetchActivities.mockReset();
    clearAutoStopCompletion.mockReset();

    fetchCharacterCurrent.mockResolvedValue(null);
    fetchActivities.mockResolvedValue(null);

    mockUseSupportFlow.mockReturnValue({
      openWelcomeMessage: vi.fn(),
      openActivityReward,
      openSupportMode: vi.fn(),
      flowState: { isOpen: false },
      flowDispatch: vi.fn(),
      handleConfirmActivity: vi.fn(),
    });

    mockUseGame.mockReturnValue({
      activityTimer: {
        currentActivity: null,
        status: 'empty',
        stop: vi.fn(),
        startActivity: vi.fn(),
        elapsed: 0,
        limitReached: false,
        autoStopCompletion: {
          xpGained: 12,
          activityName: 'Write docs',
          elapsedSeconds: 15,
        },
        clearAutoStopCompletion,
      },
      fetchCharacterCurrent,
      fetchActivities,
      loginState: 'none',
      loginStreak: 0,
      loginEventAt: null,
      player: { is_premium: false },
      freeTimerLimitSeconds: 15,
    });
  });

  it('opens the activity reward flow after an auto-stop completion', async () => {
    render(<ActivityInput />);

    await waitFor(() => {
      expect(fetchCharacterCurrent).toHaveBeenCalledTimes(1);
      expect(fetchActivities).toHaveBeenCalledTimes(1);
      expect(openActivityReward).toHaveBeenCalledWith({
        xpGained: 12,
        activityName: 'Write docs',
        elapsedSeconds: 15,
      });
      expect(clearAutoStopCompletion).toHaveBeenCalledTimes(1);
    });
  });
});
