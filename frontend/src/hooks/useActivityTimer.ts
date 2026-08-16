// hooks/useActivityTimer.ts
import { useState, useRef, useEffect, useCallback } from "react";
import { apiFetch } from "../utils/api.js";
import { playActivityStartedSound, primeAudio } from "../utils/sounds.js";
import type {
  TimerStatus,
  CurrentActivity,
  StartActivityInput,
  ActivityTimerApiData,
  ActivityCompleteResponse,
  AutoStopCompletion,
  ActivityTimerReturn,
} from "../types";
//import { useGame } from "../context/GameContext.jsx";


export default function useActivityTimer(): ActivityTimerReturn {
  const [_id, setId] = useState<number>(0);
  const [status, setStatus] = useState<TimerStatus>("empty"); // "empty", "active", "waiting", "completed"
  const [duration, setDuration] = useState<number>(0); // total seconds for timer base
  const [elapsed, setElapsed] = useState<number>(0);
  const [currentActivity, setCurrentActivity] = useState<CurrentActivity | null>(null);
  const [limitSeconds, setLimitSeconds] = useState<number | null>(null); // optional time limit
  const [limitReached, setLimitReached] = useState<boolean>(false); // true after auto-stop fires; cleared on next startActivity or stop
  const [autoStopCompletion, setAutoStopCompletion] = useState<AutoStopCompletion | null>(null);

  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const startTimeRef = useRef<number | null>(null);
  const pausedTimeRef = useRef<number>(0);

  const elapsedRef = useRef<number>(elapsed);
  useEffect(() => { elapsedRef.current = elapsed; }, [elapsed]);

  const statusRef = useRef<TimerStatus>(status);
  useEffect(() => { statusRef.current = status; }, [status]);

  const currentActivityRef = useRef<CurrentActivity | null>(currentActivity);
  useEffect(() => { currentActivityRef.current = currentActivity; }, [currentActivity]);

  // Mirror limitSeconds into a ref so tickMain can read it without stale closure issues
  const limitRef = useRef<number | null>(limitSeconds);
  useEffect(() => { limitRef.current = limitSeconds; }, [limitSeconds]);

  // Guard: ensures auto-submit fires at most once per activity
  const didAutoStopRef = useRef<boolean>(false);
  const autoStopReasonRef = useRef<string | null>(null);

  // Stable ref to stop so tickMain can call it without becoming stale
  const stopRef = useRef<ActivityTimerReturn["stop"] | null>(null);

  const normalizeLimitSeconds = useCallback((rawLimit: unknown): number | null => {
    const parsedLimit = Number(rawLimit);
    return Number.isFinite(parsedLimit) && parsedLimit > 0 ? parsedLimit : null;
  }, []);


  // ----------------------------
  // Tick the activity timer
  // ----------------------------

  const tickMain = useCallback((): void => {
    if (statusRef.current !== "active") return;
    if (!startTimeRef.current) return;

    const now = Date.now();
    const secondsPassed = Math.floor((now - startTimeRef.current) / 1000);
    let newElapsed = pausedTimeRef.current + secondsPassed;

    const limit = limitRef.current;
    if (typeof limit === "number" && limit > 0) {
      // Clamp displayed time to the limit
      if (newElapsed >= limit) {
        newElapsed = limit;
        setElapsed(newElapsed);

        // Auto-stop and submit exactly once
          if (!didAutoStopRef.current) {
            didAutoStopRef.current = true;
            setLimitReached(true);
            stopRef.current?.({
              activityName:
                currentActivityRef.current?.name || currentActivityRef.current?.text,
              elapsedSeconds: newElapsed,
              source: "auto",
              stopReason: autoStopReasonRef.current,
            });
          }
          return;
        }
    }

    setElapsed(newElapsed);
  }, []);

  // ----------------------------
  // Start timer
  // ----------------------------


  const startActivity = useCallback(async (newActivity: StartActivityInput | string): Promise<unknown> => {
    const { text, taskId, limitSeconds: newLimit, limitReason = null, allowBlank = false } =
      typeof newActivity === "string"
        ? { text: newActivity, taskId: null, limitSeconds: null, limitReason: null, allowBlank: false }
        : newActivity || {};

    if (!text?.trim() && !allowBlank) return null;

    const trimmedText = (text ?? "").trim();

    primeAudio(); // unlock AudioContext while still in user-gesture context

    // Optimistic local state
    setCurrentActivity({ text: trimmedText, taskId });
    setStatus("active");
    setElapsed(0);
    pausedTimeRef.current = 0;
    startTimeRef.current = Date.now();

    // Set time limit (null means no limit)
    const resolvedLimit = normalizeLimitSeconds(newLimit);
    setLimitSeconds(resolvedLimit);
    limitRef.current = resolvedLimit;
    autoStopReasonRef.current =
      resolvedLimit && typeof limitReason === "string" && limitReason.trim()
        ? limitReason.trim()
        : null;
    didAutoStopRef.current = false;
    setLimitReached(false);
    setAutoStopCompletion(null);

    // Ensure only one interval exists
    if (timerRef.current) clearInterval(timerRef.current);
    timerRef.current = setInterval(tickMain, 1000);

    try {
      // 1) Tell server what the activity is
      const setData = await apiFetch<{ activity_timer?: { activity?: CurrentActivity } }>(`/activity_timers/set_activity/`, {
        method: "POST",
        body: JSON.stringify({
          activityName: trimmedText,
          task_id: taskId ?? null,
          duration: 0,
        }),
      });

      //console.log("setData:", setData);
      // If server returns canonical activity object, store it
      // But don't update status yet - keep optimistic "active" state
      const serverActivity = setData?.activity_timer?.activity;
      if (serverActivity) setCurrentActivity({ taskId, ...serverActivity });

      // 2) Tell server to start timing
      const startData = await apiFetch(`/activity_timers/start/`, {
        method: "POST",
      });

      playActivityStartedSound();

      // Don't load from server here - keep optimistic state to avoid flicker
      // The timer is already running locally and will sync on next reload

      return startData;
    } catch (err) {
      console.error("Failed to start activity:", err);

      // Roll back local timer state
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
      startTimeRef.current = null;
      pausedTimeRef.current = 0;

      setStatus("empty");
      setElapsed(0);
      setCurrentActivity(null);
      setLimitSeconds(null);
      limitRef.current = null;
      autoStopReasonRef.current = null;
      didAutoStopRef.current = false;
      setLimitReached(false);

      throw err;
    }
  }, [normalizeLimitSeconds, tickMain]);


  // ----------------------------
  // Label (rename in place) the running activity
  // ----------------------------


  const labelActivity = useCallback(async (name: string, taskId: number | null = null): Promise<unknown> => {
    const trimmedName = (name ?? "").trim();
    const previousActivity = currentActivityRef.current;

    // Optimistic local update — unlike startActivity, elapsed/status/timer
    // refs are left untouched so in-progress timing isn't lost.
    setCurrentActivity((prev) => ({ ...(prev ?? {}), name: trimmedName, text: trimmedName, taskId }));

    try {
      const data = await apiFetch<{ activity_timer?: { activity?: CurrentActivity } }>(`/activity_timers/label_activity/`, {
        method: "POST",
        body: JSON.stringify({
          activityName: trimmedName,
          task_id: taskId ?? null,
        }),
      });

      const serverActivity = data?.activity_timer?.activity;
      if (serverActivity) setCurrentActivity({ taskId, ...serverActivity });

      return data;
    } catch (err) {
      console.error("Failed to label activity:", err);
      setCurrentActivity(previousActivity);
      throw err;
    }
  }, []);


  // ----------------------------
  // Stop and submit
  // ----------------------------


  const stop = useCallback(
    async ({ activityName, elapsedSeconds, source = "manual", stopReason = null }: {
      activityName?: string;
      elapsedSeconds?: number;
      source?: "manual" | "auto";
      stopReason?: string | null;
    } = {}): Promise<ActivityCompleteResponse | null> => {
    //console.log(`[useActivityTimer] Stop and submit timer`);
    //console.log("COMPLETE called", { status, duration, elapsed, currentActivity });
    //console.trace();

    if (status === "empty") return null;

    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
    startTimeRef.current = null;

    try {
      let result: ActivityCompleteResponse | null = null;
      const completedActivityName = (
        activityName ||
        currentActivityRef.current?.name ||
        currentActivityRef.current?.text ||
        ""
      ).trim();
      const completedElapsedSeconds = Number.isFinite(Number(elapsedSeconds))
        ? Number(elapsedSeconds)
        : elapsedRef.current;

      result = await apiFetch<ActivityCompleteResponse>(`/activity_timers/complete/`, {
        method: "POST",
        body: JSON.stringify({
          activityName,
          elapsedSeconds: completedElapsedSeconds,
          source,
        }),
      });
      const parsedResultDurationSeconds = Number(result?.duration_seconds);
      const resolvedCompletionElapsedSeconds = Number.isFinite(parsedResultDurationSeconds)
        ? source === "auto"
          ? Math.max(parsedResultDurationSeconds, completedElapsedSeconds)
          : parsedResultDurationSeconds
        : completedElapsedSeconds;
      // if (reset) {
      //   await apiFetch(`/activity_timers/reset/`, { method: "POST" });
      // }

      // After server confirms, clear local state
      setStatus("empty");
      setElapsed(0);
      setDuration(0);
      setCurrentActivity(null);
      setLimitSeconds(null);
      limitRef.current = null;
      autoStopReasonRef.current = null;
      didAutoStopRef.current = false;
      setLimitReached(false);
      pausedTimeRef.current = 0;

      if (source === "auto") {
        const normalizedStopReason =
          typeof stopReason === "string" && stopReason.trim()
            ? stopReason.trim()
            : null;
        setAutoStopCompletion({
          xpGained: result?.xp_gained ?? null,
          baseXp: result?.base_xp ?? null,
          xpMultiplier: result?.xp_multiplier ?? null,
          taskXpMultiplier: result?.task_xp_multiplier ?? null,
          levelUps: result?.level_ups ?? [],
          activityName: completedActivityName || null,
          elapsedSeconds: resolvedCompletionElapsedSeconds,
          ...(normalizedStopReason ? { stopReason: normalizedStopReason } : {}),
        });
      }

      return result;
    } catch (err) {
      console.error("Failed to stop timer:", err);
      // Reset local state so the user isn't left stuck in "active" with a
      // dead interval — they can retry or start a new activity.
      setStatus("empty");
      setElapsed(0);
      setDuration(0);
      setCurrentActivity(null);
      setLimitSeconds(null);
      limitRef.current = null;
      autoStopReasonRef.current = null;
      didAutoStopRef.current = false;
      setLimitReached(false);
      pausedTimeRef.current = 0;
      throw err;
    }
    },
    [status]
  );


  // Keep stopRef in sync so tickMain can call stop without stale closure issues
  useEffect(() => { stopRef.current = stop; }, [stop]);


  // ----------------------------
  // Misc methods
  // ----------------------------


  // Cleanup on unmount
  useEffect(() => {
    //console.log(`[useActivityTimer] mounted`);
    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }

    };
  }, []);


  const loadFromServer = useCallback((
    serverData: ActivityTimerApiData | null,
    { limitSeconds: incomingLimit }: { limitSeconds?: number | null } = {}
  ): void => {
    if (!serverData) return;
    //console.log("timer from server:", serverData);
    const { id, status, elapsed_time, activity } = serverData;
    // ActivityTimerApiData doesn't declare duration but the server may return it;
    // cast to access it safely and fall back to 0.
    const duration = (serverData as ActivityTimerApiData & { duration?: number }).duration ?? 0;
    const resolvedLimit = normalizeLimitSeconds(incomingLimit);
    const nextElapsed = elapsed_time || 0;
    const nextStatus: TimerStatus = status || 'empty';

    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }

    setId(id || 0);
    setStatus(nextStatus);
    setElapsed(nextElapsed);
    setDuration(duration || 0);
    setLimitSeconds(resolvedLimit);
    limitRef.current = resolvedLimit;
    autoStopReasonRef.current = null;
    didAutoStopRef.current = false;
    setLimitReached(false);
    setAutoStopCompletion(null);

    if (activity) {
      setCurrentActivity(activity);
    } else {
      setCurrentActivity(null);
    }

    if (nextStatus === 'active') {
      // startTimeRef encodes the full elapsed time, so pausedTimeRef must be 0.
      // Setting both to nextElapsed would cause tickMain to double-count.
      pausedTimeRef.current = 0;
      startTimeRef.current = Date.now() - nextElapsed * 1000;
      timerRef.current = setInterval(tickMain, 1000);
    } else {
      pausedTimeRef.current = nextElapsed;
      startTimeRef.current = null;
    }
  }, [normalizeLimitSeconds, tickMain]);

  const clearAutoStopCompletion = useCallback((): void => {
    setAutoStopCompletion(null);
  }, []);

  return {
    status,
    elapsed,
    duration,
    limitSeconds,
    limitReached,
    autoStopCompletion,
    currentActivity,
    startActivity,
    labelActivity,
    stop,
    loadFromServer,
    clearAutoStopCompletion,
  };
}
