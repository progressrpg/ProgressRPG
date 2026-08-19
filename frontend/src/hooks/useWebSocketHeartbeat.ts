// hooks/useWebSocketHeartbeat.ts
import { useEffect } from 'react';
import type { OutgoingWebSocketMessage } from '../types';

// How often to ping the server while connected, so the backend's `last_seen`
// heartbeat stays fresh and this connection isn't swept up as abandoned by
// users.tasks.reconcile_stale_online_players or, worse, treated as a dead
// session by gameplay.tasks.auto_complete_timers_for_stale_players — which
// auto-completes the player's running activity timer.
//
// Deliberately well under gameplay.tasks.STALE_TIMER_THRESHOLD, because
// browsers throttle timers in backgrounded tabs (Chrome clamps a hidden tab to
// roughly one aligned wake-up per minute once it has been hidden for five
// minutes) and stop them outright when the device sleeps. Several of these
// pings in a row can therefore arrive late — precisely when the player has
// switched away to do the real-world thing they are timing.
export const HEARTBEAT_INTERVAL_MS = 25_000;

/**
 * Keep the player's server-side `last_seen` heartbeat fresh for as long as the
 * websocket is connected.
 *
 * The interval on its own isn't enough: a throttled or suspended tab can miss
 * pings for minutes at a time. So we also ping on every signal that the page is
 * live again (returning to the foreground, regaining focus, coming back
 * online), which re-establishes the heartbeat immediately rather than waiting
 * for a wake-up the browser may defer.
 */
export function useWebSocketHeartbeat(
  isConnected: boolean,
  send: (data: OutgoingWebSocketMessage) => void,
): void {
  useEffect(() => {
    if (!isConnected) {
      return;
    }

    const ping = (): void => send({ type: 'ping' });

    // Ping straight away rather than waiting a full interval. `last_seen` is
    // stamped on connect too, but a tab reconnecting after a sleep or network
    // drop should re-stamp it without delay.
    ping();

    const intervalId = setInterval(ping, HEARTBEAT_INTERVAL_MS);

    const pingIfVisible = (): void => {
      if (document.visibilityState === 'visible') ping();
    };

    document.addEventListener('visibilitychange', pingIfVisible);
    window.addEventListener('focus', pingIfVisible);
    window.addEventListener('online', ping);

    return () => {
      clearInterval(intervalId);
      document.removeEventListener('visibilitychange', pingIfVisible);
      window.removeEventListener('focus', pingIfVisible);
      window.removeEventListener('online', ping);
    };
  }, [isConnected, send]);
}
