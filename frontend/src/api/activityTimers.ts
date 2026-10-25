// src/api/activityTimers.ts
import type { ActivityCompleteResponse, CurrentActivity } from "../types";
import { apiFetch } from "../utils/api";

/** Response shape shared by set_activity/ and label_activity/ */
export interface ActivityTimerActionResponse {
  activity_timer?: { activity?: CurrentActivity };
}

export interface SetActivityParams {
  activityName: string;
  taskId?: number | null;
  duration?: number;
  limitSeconds?: number | null;
  limitReason?: string | null;
  start?: boolean;
}

/**
 * Assign the activity and (optionally) start the clock in one round-trip -
 * see useActivityTimer.startActivity, which passes start: true so the
 * server lands directly on "active" instead of a separate start() call.
 */
export function setActivity({
  activityName,
  taskId = null,
  duration = 0,
  limitSeconds = null,
  limitReason = null,
  start = false,
}: SetActivityParams): Promise<ActivityTimerActionResponse> {
  return apiFetch<ActivityTimerActionResponse>(`/activity_timers/set_activity/`, {
    method: "POST",
    body: JSON.stringify({
      activityName,
      task_id: taskId,
      duration,
      limitSeconds,
      limitReason,
      start,
    }),
  });
}

/** Rename (and optionally re-link to a task) the running activity in place. */
export function labelActivity(
  name: string,
  taskId: number | null = null
): Promise<ActivityTimerActionResponse> {
  return apiFetch<ActivityTimerActionResponse>(`/activity_timers/label_activity/`, {
    method: "POST",
    body: JSON.stringify({
      activityName: name,
      task_id: taskId,
    }),
  });
}

/** Resume a paused session from its own banked time. */
export function startTimer(): Promise<unknown> {
  return apiFetch(`/activity_timers/start/`, { method: "POST" });
}

/** Throw away a paused session's banked time without submitting it. */
export function resetTimer(): Promise<unknown> {
  return apiFetch(`/activity_timers/reset/`, { method: "POST" });
}

/** Stop and submit the running/paused timer. */
export function completeTimer(
  activityName: string | undefined,
  elapsedSeconds: number,
  source: "manual" | "auto" = "manual"
): Promise<ActivityCompleteResponse> {
  return apiFetch<ActivityCompleteResponse>(`/activity_timers/complete/`, {
    method: "POST",
    body: JSON.stringify({ activityName, elapsedSeconds, source }),
  });
}
