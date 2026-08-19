import { act, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { HEARTBEAT_INTERVAL_MS, useWebSocketHeartbeat } from './useWebSocketHeartbeat';

/**
 * The heartbeat is what tells the backend the player is still here. If it
 * lapses for longer than gameplay.tasks.STALE_TIMER_THRESHOLD the server
 * auto-completes their running activity timer, so these tests pin down the
 * cases where a browser would otherwise leave it lapsed.
 */
describe('useWebSocketHeartbeat', () => {
  const setVisibility = (state: DocumentVisibilityState): void => {
    Object.defineProperty(document, 'visibilityState', {
      configurable: true,
      get: () => state,
    });
  };

  beforeEach(() => {
    vi.useFakeTimers();
    setVisibility('visible');
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('does not ping while disconnected', () => {
    const send = vi.fn();

    renderHook(() => useWebSocketHeartbeat(false, send));
    act(() => {
      vi.advanceTimersByTime(HEARTBEAT_INTERVAL_MS * 3);
    });

    expect(send).not.toHaveBeenCalled();
  });

  it('pings immediately on connect rather than waiting a full interval', () => {
    const send = vi.fn();

    renderHook(() => useWebSocketHeartbeat(true, send));

    expect(send).toHaveBeenCalledWith({ type: 'ping' });
    expect(send).toHaveBeenCalledTimes(1);
  });

  it('keeps pinging on the interval', () => {
    const send = vi.fn();

    renderHook(() => useWebSocketHeartbeat(true, send));
    act(() => {
      vi.advanceTimersByTime(HEARTBEAT_INTERVAL_MS * 2);
    });

    expect(send).toHaveBeenCalledTimes(3); // immediate + two intervals
  });

  it('pings as soon as a backgrounded tab becomes visible again', () => {
    const send = vi.fn();

    renderHook(() => useWebSocketHeartbeat(true, send));
    send.mockClear();

    // A hidden tab has its timers throttled, so the interval alone can't be
    // relied on to have kept the heartbeat fresh while it was away.
    setVisibility('hidden');
    act(() => {
      document.dispatchEvent(new Event('visibilitychange'));
    });
    expect(send).not.toHaveBeenCalled();

    setVisibility('visible');
    act(() => {
      document.dispatchEvent(new Event('visibilitychange'));
    });

    expect(send).toHaveBeenCalledWith({ type: 'ping' });
  });

  it('pings on window focus and when the network comes back', () => {
    const send = vi.fn();

    renderHook(() => useWebSocketHeartbeat(true, send));
    send.mockClear();

    act(() => {
      window.dispatchEvent(new Event('focus'));
      window.dispatchEvent(new Event('online'));
    });

    expect(send).toHaveBeenCalledTimes(2);
  });

  it('stops pinging and detaches listeners once disconnected', () => {
    const send = vi.fn();

    const { rerender } = renderHook(
      ({ connected }) => useWebSocketHeartbeat(connected, send),
      { initialProps: { connected: true } },
    );

    send.mockClear();
    rerender({ connected: false });

    act(() => {
      vi.advanceTimersByTime(HEARTBEAT_INTERVAL_MS * 2);
      window.dispatchEvent(new Event('focus'));
    });

    expect(send).not.toHaveBeenCalled();
  });
});
