/**
 * Shared enums and literal union types.
 */

// ---------------------------------------------------------------------------
// Feature flags
// ---------------------------------------------------------------------------

/** Groups that can be granted access to a feature */
export type AccessGroup = "all" | "premium" | "testers";

/** Feature flag value: array of groups that have access (empty = no one) */
export type FeatureFlagValue = AccessGroup[];

/** Known feature flag keys (from src/featureFlags.js) */
export type FeatureFlagKey =
  | "activityList"
  | "tasksFeature"
  | "categoriesFeature"
  | "skillsFeature"
  | "notesFeature"
  | "projectsFeature"
  | "toastsFeature"
  | "announcements"
  | "onlinePlayerCount"
  | "unified_homepage"
  | "results_mode"
  | "map"
  | "todayPointsBadge";

// ---------------------------------------------------------------------------
// Timer statuses (Timer.STATUS_CHOICES in gameplay/models.py)
// ---------------------------------------------------------------------------

export type TimerStatus = "active" | "paused" | "waiting" | "completed" | "empty";

// ---------------------------------------------------------------------------
// Character activity status (CharacterActivitySerializer.get_status)
// ---------------------------------------------------------------------------

export type CharacterActivityStatus = "past" | "current" | "future" | "unknown";

// ---------------------------------------------------------------------------
// Login / session state
// ---------------------------------------------------------------------------

/** Login state returned by /fetch_info/ */
export type LoginState = "none" | "new_login" | "returning" | string;

// ---------------------------------------------------------------------------
// WebSocket message types (gameplay/consumers.py + ServerMessage.type)
// ---------------------------------------------------------------------------

export type WebSocketMessageType =
  | "console.log"
  | "server_message"
  | "notification"
  | "event"
  | "action"
  | "response"
  | "error"
  | "pong"
  | "online_count";

// WebSocket action strings sent from client (handle_client_request)
export type ClientWebSocketAction =
  | "start_timers"
  | "pause_timers"
  | "create_activity"
  | "choose_quest"
  | "complete_quest"
  | "submit_activity";

// WebSocket action strings sent by server
export type ServerWebSocketAction =
  | "console.log"
  | "pong"
  | "no_active_character"
  | "notification"
  | "quest_complete"
  | "reward"
  | "message"
  | string;

// ---------------------------------------------------------------------------
// XP modifier scope (XpModifier.Scope)
// ---------------------------------------------------------------------------

export type XpModifierScope = "PLAYER" | "CHARACTER";

// ---------------------------------------------------------------------------
// Quest category / frequency
// ---------------------------------------------------------------------------

export type QuestCategory = "NONE" | "TRADE" | "RECUR" | "EVENT";
export type QuestFrequency = "NONE" | "DAY" | "WEEK" | "MONTH";

// ---------------------------------------------------------------------------
// Subscription plan
// ---------------------------------------------------------------------------

export type SubscriptionPlan = "monthly" | "annual";
