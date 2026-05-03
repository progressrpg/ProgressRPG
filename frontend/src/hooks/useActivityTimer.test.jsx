import { act, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import useActivityTimer from './useActivityTimer';

const mockApiFetch = vi.fn();
const mockPlayActivityStartedSound = vi.fn();

vi.mock("../utils/api.js", () => ({
  apiFetch: (...args) => mockApiFetch(...args),
}));

vi.mock("../utils/sounds.js", () => ({
  playActivityStartedSound: (...args) => mockPlayActivityStartedSound(...args),
}));

describe('useActivityTimer', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    mockApiFetch.mockReset();
    mockPlayActivityStartedSound.mockReset();
  });

  afterEach(() => {
    act(() => {
      vi.runOnlyPendingTimers();
    });
    vi.useRealTimers();
  });

  it('auto-stops when a new timer reaches its configured limit', async () => {
    mockApiFetch.mockImplementation((url) => {
      if (url === '/activity_timers/set_activity/') {
        return Promise.resolve({
          activity_timer: {
            activity: { id: 1, name: 'Test activity' },
          },
        });
      }

      if (url === '/activity_timers/start/') {
        return Promise.resolve({ success: true });
      }

      if (url === '/activity_timers/complete/') {
        return Promise.resolve({ xp_gained: 15, base_xp: 15, xp_multiplier: 1, level_ups: [2], duration_seconds: 15 });
      }

      return Promise.reject(new Error(`Unexpected URL: ${url}`));
    });

    const { result } = renderHook(() => useActivityTimer());

    await act(async () => {
      await result.current.startActivity({ text: 'Test activity', limitSeconds: 15 });
    });

    await act(async () => {
      await vi.advanceTimersByTimeAsync(15_000);
    });

    expect(mockApiFetch).toHaveBeenCalledWith(
      '/activity_timers/complete/',
      expect.objectContaining({ method: 'POST' })
    );
    expect(mockPlayActivityStartedSound).toHaveBeenCalledTimes(1);
    expect(result.current.status).toBe('empty');
    expect(result.current.elapsed).toBe(0);
    expect(result.current.autoStopCompletion).toEqual({
      xpGained: 15,
      baseXp: 15,
      xpMultiplier: 1,
      levelUps: [2],
      activityName: 'Test activity',
      elapsedSeconds: 15,
    });
  });

  it('restores limit enforcement for active timers loaded from the server', async () => {
    mockApiFetch.mockResolvedValue({ xp_gained: 15, base_xp: 15, xp_multiplier: 1, level_ups: [], duration_seconds: 14 });

    const { result } = renderHook(() => useActivityTimer());

    act(() => {
      result.current.loadFromServer(
        {
          id: 1,
          status: 'active',
          elapsed_time: 14,
          duration: 0,
          activity: { id: 1, name: 'Restored activity' },
        },
        { limitSeconds: 15 }
      );
    });

    await act(async () => {
      await vi.advanceTimersByTimeAsync(1_000);
    });

    expect(mockApiFetch).toHaveBeenCalledWith(
      '/activity_timers/complete/',
      expect.objectContaining({ method: 'POST' })
    );
    expect(result.current.status).toBe('empty');
    expect(result.current.limitSeconds).toBe(null);
    expect(result.current.autoStopCompletion).toEqual({
      xpGained: 15,
      baseXp: 15,
      xpMultiplier: 1,
      levelUps: [],
      activityName: 'Restored activity',
      elapsedSeconds: 15,
    });
  });

  it('plays the start chime when an activity starts successfully', async () => {
    mockApiFetch.mockImplementation((url) => {
      if (url === '/activity_timers/set_activity/') {
        return Promise.resolve({
          activity_timer: {
            activity: { id: 1, name: 'Chime activity' },
          },
        });
      }

      if (url === '/activity_timers/start/') {
        return Promise.resolve({ success: true });
      }

      return Promise.reject(new Error(`Unexpected URL: ${url}`));
    });

    const { result } = renderHook(() => useActivityTimer());

    await act(async () => {
      await result.current.startActivity({ text: 'Chime activity', limitSeconds: 15 });
    });

    expect(mockPlayActivityStartedSound).toHaveBeenCalledTimes(1);
  });
});
