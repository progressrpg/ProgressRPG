import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import ActivityInput from './ActivityInput';

const mockUseGame = vi.fn();
const mockUseSupportFlow = vi.fn();
const openActivityReward = vi.fn();
const fetchPlayerAndCharacter = vi.fn();
const fetchCharacterCurrent = vi.fn();
const fetchActivities = vi.fn();
const clearAutoStopCompletion = vi.fn();
const stop = vi.fn();
const startActivity = vi.fn();
const addEntityToCache = vi.fn();
const { playLimitReachedSound } = vi.hoisted(() => ({
  playLimitReachedSound: vi.fn(),
}));

vi.mock('../../context/GameContext', () => ({
  useGame: () => mockUseGame(),
}));

vi.mock('../../hooks/useSupportFlow', () => ({
  useSupportFlow: (...args) => mockUseSupportFlow(...args),
}));

vi.mock('../../hooks/useEntitySearchCache', () => ({
  useEntitySearchCache: () => ({
    addEntityToCache,
  }),
}));

vi.mock('../SupportFlow/SupportFlowModal', () => ({
  default: () => null,
}));

vi.mock('../EntitySearchInput/EntitySearchInput', () => ({
  default: ({ value, onChange, ariaLabel, inputClassName }) => (
    <input
      value={value}
      onChange={(event) => onChange(event.target.value)}
      aria-label={ariaLabel}
      className={inputClassName}
    />
  ),
}));

vi.mock('../../utils/sounds', () => ({
  playLimitReachedSound,
}));

describe('ActivityInput', () => {
  beforeEach(() => {
    openActivityReward.mockReset();
    fetchPlayerAndCharacter.mockReset();
    fetchCharacterCurrent.mockReset();
    fetchActivities.mockReset();
    clearAutoStopCompletion.mockReset();
    stop.mockReset();
    startActivity.mockReset();
    addEntityToCache.mockReset();
    playLimitReachedSound.mockReset();

    fetchPlayerAndCharacter.mockResolvedValue(null);
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
        stop,
        startActivity,
        elapsed: 0,
        limitSeconds: null,
        limitReached: false,
        autoStopCompletion: {
          xpGained: 12,
          baseXp: 6,
          xpMultiplier: 2,
          levelUps: [3],
          stopReason: 'free_limit',
          activityName: 'Write docs',
          elapsedSeconds: 15,
        },
        clearAutoStopCompletion,
      },
      fetchPlayerAndCharacter,
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
      expect(fetchPlayerAndCharacter).toHaveBeenCalledTimes(1);
      expect(fetchCharacterCurrent).toHaveBeenCalledTimes(1);
      expect(fetchActivities).toHaveBeenCalledTimes(1);
      expect(openActivityReward).toHaveBeenCalledWith({
        xpGained: 12,
        baseXp: 6,
        xpMultiplier: 2,
        levelUps: [3],
        isAutoStopped: true,
        showUpgradePrompt: true,
        activityName: 'Write docs',
        elapsedSeconds: 15,
      });
      expect(playLimitReachedSound).toHaveBeenCalledTimes(1);
      expect(clearAutoStopCompletion).toHaveBeenCalledTimes(1);
    });
  });

  it('refreshes player data after a manual stop so the infobar updates xp', async () => {
    const user = userEvent.setup();
    stop.mockResolvedValue({ xp_gained: 16, base_xp: 16, xp_multiplier: 1, level_ups: [2], duration_seconds: 16 });

    mockUseGame.mockReturnValue({
      activityTimer: {
        currentActivity: { name: 'Write docs' },
        status: 'active',
        stop,
        startActivity,
        elapsed: 15,
        limitSeconds: 15,
        limitReached: false,
        autoStopCompletion: null,
        clearAutoStopCompletion,
      },
      fetchPlayerAndCharacter,
      fetchCharacterCurrent,
      fetchActivities,
      loginState: 'none',
      loginStreak: 0,
      loginEventAt: null,
      player: { is_premium: false },
      freeTimerLimitSeconds: 15,
    });

    render(<ActivityInput />);

    await user.click(screen.getByRole('button', { name: 'Stop' }));

    await waitFor(() => {
      expect(stop).toHaveBeenCalledWith({ activityName: 'Write docs' });
      expect(fetchPlayerAndCharacter).toHaveBeenCalledTimes(1);
      expect(fetchCharacterCurrent).toHaveBeenCalledTimes(1);
      expect(fetchActivities).toHaveBeenCalledTimes(1);
      expect(openActivityReward).toHaveBeenCalledWith({
        xpGained: 16,
        baseXp: 16,
        xpMultiplier: 1,
        levelUps: [2],
        isAutoStopped: false,
        showUpgradePrompt: true,
        activityName: 'Write docs',
        elapsedSeconds: 16,
      });
      expect(playLimitReachedSound).toHaveBeenCalledTimes(1);
    });
  });

  it('does not show free-limit upgrade prompt for non-free auto-stop reasons', async () => {
    mockUseGame.mockReturnValue({
      activityTimer: {
        currentActivity: null,
        status: 'empty',
        stop,
        startActivity,
        elapsed: 0,
        limitSeconds: null,
        limitReached: false,
        autoStopCompletion: {
          xpGained: 12,
          baseXp: 6,
          xpMultiplier: 2,
          levelUps: [3],
          stopReason: 'preset_limit',
          activityName: 'Write docs',
          elapsedSeconds: 15,
        },
        clearAutoStopCompletion,
      },
      fetchPlayerAndCharacter,
      fetchCharacterCurrent,
      fetchActivities,
      loginState: 'none',
      loginStreak: 0,
      loginEventAt: null,
      player: { is_premium: false },
      freeTimerLimitSeconds: 15,
    });

    render(<ActivityInput />);

    await waitFor(() => {
      expect(openActivityReward).toHaveBeenCalledWith({
        xpGained: 12,
        baseXp: 6,
        xpMultiplier: 2,
        levelUps: [3],
        isAutoStopped: true,
        showUpgradePrompt: false,
        activityName: 'Write docs',
        elapsedSeconds: 15,
      });
    });
  });

  it('shows an auto-stop warning after 90 percent of a limited timer has elapsed', () => {
    mockUseGame.mockReturnValue({
      activityTimer: {
        currentActivity: { name: 'Write docs' },
        status: 'active',
        stop,
        startActivity,
        elapsed: 27,
        limitSeconds: 30,
        limitReached: false,
        autoStopCompletion: null,
        clearAutoStopCompletion,
      },
      fetchPlayerAndCharacter,
      fetchCharacterCurrent,
      fetchActivities,
      loginState: 'none',
      loginStreak: 0,
      loginEventAt: null,
      player: { is_premium: false },
      freeTimerLimitSeconds: 30,
    });

    render(<ActivityInput />);

    expect(
      screen.getByText('This timer will stop automatically when it reaches 0:30.')
    ).toBeInTheDocument();
  });

  it('does not show the auto-stop warning before 90 percent of the limit', () => {
    mockUseGame.mockReturnValue({
      activityTimer: {
        currentActivity: { name: 'Write docs' },
        status: 'active',
        stop,
        startActivity,
        elapsed: 26,
        limitSeconds: 30,
        limitReached: false,
        autoStopCompletion: null,
        clearAutoStopCompletion,
      },
      fetchPlayerAndCharacter,
      fetchCharacterCurrent,
      fetchActivities,
      loginState: 'none',
      loginStreak: 0,
      loginEventAt: null,
      player: { is_premium: false },
      freeTimerLimitSeconds: 30,
    });

    render(<ActivityInput />);

    expect(
      screen.queryByText('This timer will stop automatically when it reaches 0:30.')
    ).not.toBeInTheDocument();
  });
});
