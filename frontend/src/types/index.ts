/**
 * Barrel export for all shared TypeScript types.
 *
 * Import from here in consuming files:
 *   import type { Player, Character, TimerStatus } from "../types";
 */

// Generic API response shapes
export type {
  PaginatedResponse,
  ApiErrorResponse,
  TokenPair,
  AccessTokenResponse,
  CheckoutSessionResponse,
  AppConfig,
  RegistrationStatus,
  GameSettings,
  FetchInfoResponse,
  AnnouncementListResponse,
  AnnouncementUnreadCountResponse,
  AnnouncementReadMutationResponse,
  OfflineActivityLogResponse,
} from "./api";

// Enums and literal union types
export type {
  AccessGroup,
  FeatureFlagValue,
  FeatureFlagKey,
  TimerStatus,
  CharacterActivityStatus,
  LoginState,
  WebSocketMessageType,
  ClientWebSocketAction,
  ServerWebSocketAction,
  XpModifierScope,
  SubscriptionPlan,
} from "./enums";

// Domain interfaces
export type {
  User,
  Player,
  Announcement,
  AchievementGoal,
  Character,
  GeoJSONPoint,
  PlayerSkill,
  Category,
  PlayerActivity,
  CharacterActivity,
  Project,
  Task,
  Note,
  XpModifier,
  PopulationCentre,
  Building,
  TutorialStep,
} from "./domain";

// Timer types
export type {
  ActivityTimerApiData,
  ActivityCompleteResponse,
  CurrentActivity,
  StartActivityInput,
  AutoStopCompletion,
  ActivityTimerReturn,
  WebSocketMessageBase,
  WebSocketConsoleMessage,
  WebSocketPongMessage,
  WebSocketNotificationMessage,
  WebSocketErrorMessage,
  WebSocketActionMessage,
  WebSocketServerMessage,
  IncomingWebSocketMessage,
  OutgoingWebSocketMessage,
} from "./timers";
