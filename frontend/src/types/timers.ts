/**
 * Timer-related types — activity timer state, WebSocket message shapes,
 * and the return type of useActivityTimer.
 */

import type { TimerStatus, WebSocketMessageType, ServerWebSocketAction, ClientWebSocketAction } from "./enums";
import type { PlayerActivity } from "./domain";

// ---------------------------------------------------------------------------
// Activity timer API shape (ActivityTimerSerializer)
// ---------------------------------------------------------------------------

/** Raw shape returned from /activity_timers/ endpoints */
export interface ActivityTimerApiData {
  id: number;
  status: TimerStatus;
  elapsed_time: number;
  created_at: string;
  last_updated: string;
  activity: PlayerActivity | null;
  player: number;
}

/** Response from POST /activity_timers/complete/ */
export interface ActivityCompleteResponse {
  duration_seconds: number;
  base_xp: number;
  xp_multiplier: number;
  task_xp_multiplier?: number;
  xp_gained: number;
  level_ups: number[];
}

// ---------------------------------------------------------------------------
// useActivityTimer hook state and return value
// ---------------------------------------------------------------------------

/**
 * The current activity as held in local hook state.
 * This may be the full server PlayerActivity or a lightweight optimistic object.
 */
export interface CurrentActivity {
  /** Display name (from server activity.name or optimistic text) */
  name?: string;
  /** Optimistic text before server confirmation */
  text?: string;
  /** Optional task ID the activity is logged against */
  taskId?: number | null;
  /** Server-assigned id once confirmed (this timed session's PlayerActivity id) */
  id?: number;
  /**
   * FK to the reusable Activity "type" (catalog entry) this session resolved
   * to — stable across separate start/stop cycles of the same-named,
   * task-less activity, unlike `id` above.
   */
  activity?: number | null;
}

/**
 * Payload passed to startActivity when starting a new timer.
 * A plain string is also accepted (treated as `{ text: string }`).
 */
export interface StartActivityInput {
  text: string;
  taskId?: number | null;
  /** Optional hard cap in seconds — timer auto-stops when reached */
  limitSeconds?: number | null;
  /** Human-readable reason for the limit (shown in auto-stop notification) */
  limitReason?: string | null;
  /** Explicitly allow starting with blank/empty text (e.g. "Blank Start") */
  allowBlank?: boolean;
}

/**
 * Payload set when the timer auto-stops due to hitting limitSeconds.
 * Stored in autoStopCompletion state until cleared.
 */
export interface AutoStopCompletion {
  xpGained: number | null;
  baseXp: number | null;
  xpMultiplier: number | null;
  taskXpMultiplier: number | null;
  levelUps: number[];
  activityName: string | null;
  elapsedSeconds: number;
  stopReason?: string;
}

/** Full return shape of useActivityTimer */
export interface ActivityTimerReturn {
  status: TimerStatus;
  elapsed: number;
  duration: number;
  limitSeconds: number | null;
  limitReached: boolean;
  autoStopCompletion: AutoStopCompletion | null;
  currentActivity: CurrentActivity | null;
  startActivity: (newActivity: StartActivityInput | string) => Promise<unknown>;
  /**
   * Rename (and optionally re-link to a task) the activity already assigned
   * to a running/waiting timer, in place — unlike startActivity, this does
   * not reset elapsed time or status.
   */
  labelActivity: (name: string, taskId?: number | null) => Promise<unknown>;
  stop: (opts?: {
    activityName?: string;
    elapsedSeconds?: number;
    source?: "manual" | "auto";
    stopReason?: string | null;
  }) => Promise<ActivityCompleteResponse | null>;
  loadFromServer: (
    serverData: ActivityTimerApiData | null,
    opts?: { limitSeconds?: number | null }
  ) => void;
  clearAutoStopCompletion: () => void;
}

// ---------------------------------------------------------------------------
// WebSocket message shapes
// ---------------------------------------------------------------------------

/** Base shape for all WebSocket messages */
export interface WebSocketMessageBase {
  type: WebSocketMessageType;
  action: ServerWebSocketAction;
  message?: string;
}

/** console.log / pong messages */
export interface WebSocketConsoleMessage extends WebSocketMessageBase {
  type: "console.log";
  action: "console.log";
  message: string;
}

export interface WebSocketPongMessage extends WebSocketMessageBase {
  type: "pong";
  action: "pong";
  message: "pong";
}

/** Notification message (quest complete, activity submitted, etc.) */
export interface WebSocketNotificationMessage extends WebSocketMessageBase {
  type: "notification";
  action: "notification";
  data?: Record<string, unknown>;
  created_at?: string;
}

/** Error message sent by server */
export interface WebSocketErrorMessage extends WebSocketMessageBase {
  type: "error";
  action: ServerWebSocketAction;
  message: string;
}

/** Server-initiated action message (maintenance refresh, game events) */
export interface WebSocketActionMessage {
  type: "action";
  action: "refresh" | "load-game" | "activity_timer_update" | "announcement_published";
  message?: string;
  maintenance_active?: boolean;
  name?: string;
  description?: string;
  start_time?: string | null;
  end_time?: string | null;
  /**
   * Present when action is "activity_timer_update" — pushed whenever another
   * of this player's sessions (tabs/devices) starts, labels, or submits the
   * activity timer, so every open session can reconcile to server state.
   *
   * Present when action is "announcement_published" — the id of the
   * newly-published Announcement, so callers can invalidate the
   * announcements list and unread-count queries.
   */
  data?: { activity_timer: ActivityTimerApiData } | { id: number };
}

/** Generic server message (currently unused payload) */
export interface WebSocketServerMessage {
  type: "server_message";
  action?: string;
  message?: string;
}

export interface WebSocketOnlineCountMessage {
  type: "online_count";
  count: number;
}

/** Union of all known incoming WebSocket message shapes */
export type IncomingWebSocketMessage =
  | WebSocketConsoleMessage
  | WebSocketPongMessage
  | WebSocketNotificationMessage
  | WebSocketErrorMessage
  | WebSocketActionMessage
  | WebSocketServerMessage
  | WebSocketOnlineCountMessage;

/** Client-to-server message shape */
export interface OutgoingWebSocketMessage {
  type: "client_request" | "ping";
  action?: ClientWebSocketAction;
  [key: string]: unknown;
}
