import { act, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import useActivityTimer from './useActivityTimer';
import type { ActivityTimerApiData } from '../types';

const mockApiFetch = vi.fn();
const mockPlayActivityStartedSound = vi.fn();

vi.mock("../utils/api", () => ({
  apiFetch: (...args: unknown[]) => mockApiFetch(...args),
}));

vi.mock("../utils/sounds", () => ({
  playActivityStartedSound: (...args: unknown[]) => mockPlayActivityStartedSound(...args),
  primeAudio: vi.fn(),
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
    mockApiFetch.mockImplementation((url: string) => {
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
      taskXpMultiplier: null,
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
        } as unknown as ActivityTimerApiData,
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
      taskXpMultiplier: null,
      levelUps: [],
      activityName: 'Restored activity',
      elapsedSeconds: 15,
    });
  });

  it('takes the limit from the server payload, not the caller fallback', async () => {
    // Regression: both loadFromServer call sites used to rebuild the limit
    // as `is_premium ? null : freeTimerLimitSeconds`, so a custom duration
    // vanished on every reload and websocket reconciliation.
    mockApiFetch.mockResolvedValue({ xp_gained: 0, base_xp: 0, xp_multiplier: 1, level_ups: [], duration_seconds: 0 });

    const { result } = renderHook(() => useActivityTimer());

    act(() => {
      result.current.loadFromServer(
        {
          id: 1,
          status: 'active',
          elapsed_time: 10,
          activity: { id: 1, name: 'Declared 45 minutes' },
          limit_seconds: 2700,
          limit_reason: 'preset_limit',
        } as unknown as ActivityTimerApiData,
        // What the caller would previously have forced for a premium user.
        { limitSeconds: null }
      );
    });

    expect(result.current.limitSeconds).toBe(2700);
  });

  it('plays the start chime when an activity starts successfully', async () => {
    mockApiFetch.mockImplementation((url: string) => {
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

  it('rejects a blank start without allowBlank', async () => {
    const { result } = renderHook(() => useActivityTimer());

    await act(async () => {
      const outcome = await result.current.startActivity({ text: '' });
      expect(outcome).toBeNull();
    });

    expect(mockApiFetch).not.toHaveBeenCalled();
    expect(result.current.status).toBe('empty');
  });

  it('starts an unlabelled timer when allowBlank is set', async () => {
    mockApiFetch.mockImplementation((url: string) => {
      if (url === '/activity_timers/set_activity/') {
        return Promise.resolve({
          activity_timer: { activity: { id: 1, name: '' } },
        });
      }

      if (url === '/activity_timers/start/') {
        return Promise.resolve({ success: true });
      }

      return Promise.reject(new Error(`Unexpected URL: ${url}`));
    });

    const { result } = renderHook(() => useActivityTimer());

    await act(async () => {
      await result.current.startActivity({ text: '', allowBlank: true });
    });

    expect(mockApiFetch).toHaveBeenCalledWith(
      '/activity_timers/set_activity/',
      expect.objectContaining({
        body: JSON.stringify({
          activityName: '',
          task_id: null,
          duration: 0,
          // Sent so the server can enforce the bound itself; null here
          // because an unlabelled quick-start declares no duration.
          limitSeconds: null,
          limitReason: null,
          // set_activity assigns the activity and starts the clock in one
          // round-trip (see useActivityTimer's comment on the call site).
          start: true,
        }),
      })
    );
    expect(result.current.status).toBe('active');
    expect(result.current.currentActivity?.name).toBe('');
  });

  it('labelActivity renames the running activity without resetting elapsed time', async () => {
    mockApiFetch.mockImplementation((url: string) => {
      if (url === '/activity_timers/set_activity/') {
        return Promise.resolve({
          activity_timer: { activity: { id: 1, name: '' } },
        });
      }

      if (url === '/activity_timers/start/') {
        return Promise.resolve({ success: true });
      }

      if (url === '/activity_timers/label_activity/') {
        return Promise.resolve({
          activity_timer: { activity: { id: 1, name: 'Deep work' } },
        });
      }

      return Promise.reject(new Error(`Unexpected URL: ${url}`));
    });

    const { result } = renderHook(() => useActivityTimer());

    await act(async () => {
      await result.current.startActivity({ text: '', allowBlank: true });
    });

    await act(async () => {
      await vi.advanceTimersByTimeAsync(5_000);
    });

    const elapsedBeforeLabel = result.current.elapsed;
    expect(elapsedBeforeLabel).toBeGreaterThan(0);

    await act(async () => {
      await result.current.labelActivity('Deep work');
    });

    expect(mockApiFetch).toHaveBeenCalledWith(
      '/activity_timers/label_activity/',
      expect.objectContaining({
        body: JSON.stringify({ activityName: 'Deep work', task_id: null }),
      })
    );
    expect(result.current.currentActivity?.name).toBe('Deep work');
    expect(result.current.status).toBe('active');
    expect(result.current.elapsed).toBe(elapsedBeforeLabel);
  });

  it('labelActivity rolls back the optimistic name on failure', async () => {
    mockApiFetch.mockImplementation((url: string) => {
      if (url === '/activity_timers/set_activity/') {
        return Promise.resolve({
          activity_timer: { activity: { id: 1, name: 'Original' } },
        });
      }

      if (url === '/activity_timers/start/') {
        return Promise.resolve({ success: true });
      }

      if (url === '/activity_timers/label_activity/') {
        return Promise.reject(new Error('network error'));
      }

      return Promise.reject(new Error(`Unexpected URL: ${url}`));
    });

    const { result } = renderHook(() => useActivityTimer());

    await act(async () => {
      await result.current.startActivity({ text: 'Original' });
    });

    await act(async () => {
      await expect(result.current.labelActivity('New name')).rejects.toThrow('network error');
    });

    expect(result.current.currentActivity?.name).toBe('Original');
  });
});
