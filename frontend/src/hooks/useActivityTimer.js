// hooks/useActivityTimer.js
import { useState, useRef, useEffect, useCallback } from "react";
import { apiFetch } from "../../utils/api.js";
//import { useGame } from "../context/GameContext.jsx";


export default function useActivityTimer() {
  const [id, setId] = useState(0);
  const [status, setStatus] = useState("empty"); // "empty", "active", "waiting", "completed"
  const [duration, setDuration] = useState(0); // total seconds for timer base
  const [elapsed, setElapsed] = useState(0);
  const [currentActivity, setCurrentActivity] = useState(null);
  const [limitSeconds, setLimitSeconds] = useState(null); // optional time limit
  const [limitReached, setLimitReached] = useState(false); // true after auto-stop fires; cleared on next startActivity or stop

  const timerRef = useRef(null);
  const startTimeRef = useRef(null);
  const pausedTimeRef = useRef(0);

  const elapsedRef = useRef(elapsed);
  useEffect(() => { elapsedRef.current = elapsed; }, [elapsed]);

  const statusRef = useRef(status);
  useEffect(() => { statusRef.current = status; }, [status]);

  // Mirror limitSeconds into a ref so tickMain can read it without stale closure issues
  const limitRef = useRef(limitSeconds);
  useEffect(() => { limitRef.current = limitSeconds; }, [limitSeconds]);

  // Guard: ensures auto-submit fires at most once per activity
  const didAutoStopRef = useRef(false);

  // Stable ref to stop so tickMain can call it without becoming stale
  const stopRef = useRef(null);


  // ----------------------------
  // Tick the activity timer
  // ----------------------------

  const tickMain = useCallback(() => {
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
          stopRef.current?.();
        }
        return;
      }
    }

    setElapsed(newElapsed);
  }, []);

  // ----------------------------
  // Start timer
  // ----------------------------


  const startActivity = useCallback(async (newActivity) => {
    const { text, taskId, limitSeconds: newLimit } =
      typeof newActivity === "string"
        ? { text: newActivity, taskId: null, limitSeconds: null }
        : newActivity || {};

    if (!text?.trim()) return null;

    // Optimistic local state
    setCurrentActivity({ text: text.trim(), taskId });
    setStatus("active");
    setElapsed(0);
    pausedTimeRef.current = 0;
    startTimeRef.current = Date.now();

    // Set time limit (null means no limit)
    const resolvedLimit = Number.isFinite(newLimit) && newLimit > 0 ? newLimit : null;
    setLimitSeconds(resolvedLimit);
    limitRef.current = resolvedLimit;
    didAutoStopRef.current = false;
    setLimitReached(false);

    // Ensure only one interval exists
    if (timerRef.current) clearInterval(timerRef.current);
    timerRef.current = setInterval(tickMain, 1000);

    try {
      // 1) Tell server what the activity is
      const setData = await apiFetch(`/activity_timers/set_activity/`, {
        method: "POST",
        body: JSON.stringify({
          activityName: text.trim(),
          task_id: taskId ?? null,
          duration: 0,
        }),
      });

      //console.log("setData:", setData);
      // If server returns canonical activity object, store it
      // But don't update status yet - keep optimistic "active" state
      const serverActivity = setData?.activity_timer?.activity;
      if (serverActivity) setCurrentActivity(serverActivity);

      // 2) Tell server to start timing
      const startData = await apiFetch(`/activity_timers/start/`, {
        method: "POST",
      });

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
      didAutoStopRef.current = false;
      setLimitReached(false);

      throw err;
    }
  }, [tickMain]);


  // ----------------------------
  // Stop and submit
  // ----------------------------


  const stop = useCallback(async ({ activityName } = {}) => {
    //console.log(`[useActivityTimer] Stop and submit timer`);
    //console.log("COMPLETE called", { status, duration, elapsed, currentActivity });
    //console.trace();

    if (status === "empty") return;

    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
    startTimeRef.current = null;

    try {
      let result = null;

      result = await apiFetch(`/activity_timers/complete/`, { method: "POST", body: JSON.stringify({activityName}) });
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
      didAutoStopRef.current = false;
      setLimitReached(false);
      pausedTimeRef.current = 0;

      return result;
    } catch (err) {
      console.error("Failed to stop timer:", err);
      // You might want to restore interval here if status was active,
      // but for MVP it's okay to leave it stopped and let user retry.
      throw err;
    }
  }, [status]);


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


  const loadFromServer = useCallback((serverData) => {
    if (!serverData) return;
    //console.log("timer from server:", serverData);
    const { id, status, elapsed_time, duration, activity } = serverData;

    setId(id || 0);
    setStatus(status || 'empty');
    setElapsed(elapsed_time || 0);
    setDuration(duration || 0);

    if (activity) {
      setCurrentActivity(activity);
    }
  }, []);

  return {
    status,
    elapsed,
    duration,
    limitSeconds,
    limitReached,
    currentActivity,
    startActivity,
    stop,
    loadFromServer,
  };
}
