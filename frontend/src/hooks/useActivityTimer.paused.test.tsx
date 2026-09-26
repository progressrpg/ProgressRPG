import { act, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import useActivityTimer from './useActivityTimer';
import type { ActivityTimerApiData } from '../types';

const mockApiFetch = vi.fn();

vi.mock('../utils/api', () => ({
  apiFetch: (...args: unknown[]) => mockApiFetch(...args),
}));

vi.mock('../utils/sounds', () => ({
  playActivityStartedSound: vi.fn(),
  primeAudio: vi.fn(),
}));

function pausedSnapshot(overrides: Record<string, unknown> = {}) {
  return {
    id: 1,
    status: 'paused',
    elapsed_time: 600,
    activity: { id: 1, name: 'Interrupted session' },
    limit_seconds: null,
    limit_reason: '',
    can_resume: true,
    ...overrides,
  } as unknown as ActivityTimerApiData;
}

/**
 * A paused session holds the player's banked time. The client has to
 * represent it as a session — treating it as "no timer" is what made the
 * next start wipe the time instead of preserving it.
 */
describe('useActivityTimer paused sessions', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    mockApiFetch.mockReset();
  });

  afterEach(() => {
    act(() => {
      vi.runOnlyPendingTimers();
    });
    vi.useRealTimers();
  });

  it('shows banked time without ticking', () => {
    const { result } = renderHook(() => useActivityTimer());

    act(() => {
      result.current.loadFromServer(pausedSnapshot());
    });

    expect(result.current.status).toBe('paused');
    expect(result.current.elapsed).toBe(600);

    act(() => {
      vi.advanceTimersByTime(5_000);
    });

    // Still 600: a paused session must not accrue.
    expect(result.current.elapsed).toBe(600);
  });

  it('resumes from the banked time rather than restarting at zero', async () => {
    mockApiFetch.mockResolvedValue({ success: true });
    const { result } = renderHook(() => useActivityTimer());

    act(() => {
      result.current.loadFromServer(pausedSnapshot());
    });

    await act(async () => {
      await result.current.resume();
    });

    expect(mockApiFetch).toHaveBeenCalledWith(
      '/activity_timers/start/',
      expect.objectContaining({ method: 'POST' })
    );
    expect(result.current.status).toBe('active');

    await act(async () => {
      await vi.advanceTimersByTimeAsync(3_000);
    });

    expect(result.current.elapsed).toBeGreaterThanOrEqual(603);
  });

  it('keeps the banked time when resuming fails', async () => {
    mockApiFetch.mockRejectedValue(new Error('offline'));
    const { result } = renderHook(() => useActivityTimer());

    act(() => {
      result.current.loadFromServer(pausedSnapshot());
    });

    await act(async () => {
      await expect(result.current.resume()).rejects.toThrow('offline');
    });

    // Rolled back to paused with the time intact — nothing is lost, the
    // player can simply try again.
    expect(result.current.status).toBe('paused');
    expect(result.current.elapsed).toBe(600);
  });

  it('takes canResume from the server rather than deciding locally', () => {
    const { result } = renderHook(() => useActivityTimer());

    act(() => {
      result.current.loadFromServer(pausedSnapshot({ can_resume: false }));
    });

    expect(result.current.canResume).toBe(false);
    expect(result.current.status).toBe('paused');
    // The time is still there to submit, just not to continue.
    expect(result.current.elapsed).toBe(600);
  });

  it('discard clears the session through the reset endpoint', async () => {
    mockApiFetch.mockResolvedValue({ success: true });
    const { result } = renderHook(() => useActivityTimer());

    act(() => {
      result.current.loadFromServer(pausedSnapshot());
    });

    await act(async () => {
      await result.current.discard();
    });

    expect(mockApiFetch).toHaveBeenCalledWith(
      '/activity_timers/reset/',
      expect.objectContaining({ method: 'POST' })
    );
    expect(result.current.status).toBe('empty');
    expect(result.current.elapsed).toBe(0);
  });

  it('resume is a no-op when nothing is paused', async () => {
    const { result } = renderHook(() => useActivityTimer());

    await act(async () => {
      const outcome = await result.current.resume();
      expect(outcome).toBeNull();
    });

    expect(mockApiFetch).not.toHaveBeenCalled();
  });
});
