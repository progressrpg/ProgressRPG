/**
 * Generic API response shapes shared across all endpoints.
 */

/** Standard DRF paginated list response */
export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

/** Standard error response body */
export interface ApiErrorResponse {
  error?: string;
  detail?: string;
  [field: string]: string | string[] | undefined;
}

/** Auth token pair returned on login */
export interface TokenPair {
  access_token: string;
  refresh_token: string;
}

/** Auth token returned on refresh */
export interface AccessTokenResponse {
  access_token: string;
}

/** Checkout session URL response */
export interface CheckoutSessionResponse {
  url: string;
}

/** App config (public, unauthenticated) */
export interface AppConfig {
  stripe_live_mode: boolean;
  stripe_billing_portal_url: string;
  feature_flags: Record<string, string>;
  trial_period_days: number;
}

/** Registration status (public, unauthenticated) */
export interface RegistrationStatus {
  registration_open: boolean;
  registration_enabled: boolean;
  self_serve_registration: boolean;
  /** Which waitlist signup flow the "join the waitlist" forms should use. */
  waitlist_signup_provider: 'mailchimp' | 'internal';
  /** Public Cloudflare Turnstile site key; empty when Turnstile is unconfigured. */
  turnstile_site_key?: string;
}

/** Game settings returned in fetch_info and /game_settings/ */
export interface GameSettings {
  free_timer_limit_seconds: number;
  daily_login_base_xp: number;
  daily_login_streak_step_xp: number;
  daily_login_max_xp: number;
  premium_activity_xp_multiplier: number;
  default_activity_xp_per_second: number;
  activity_search_includes_tasks: boolean;
}

/** Bootstrap response from /fetch_info/ */
export interface FetchInfoResponse {
  success: boolean;
  message: string;
  build_number: string;
  player: Player;
  character: Character | null;
  activity_timer: ActivityTimerApiData | null;
  population_centre: PopulationCentre | null;
  xp_mods: XpModifier[];
  login_state: LoginState;
  login_streak: number;
  login_event_at: string | null;
  login_reward_xp: number;
  announcement_unread_count: number;
  free_timer_limit_seconds: number;
  game_settings: GameSettings;
  online_count: number;
}

export interface AnnouncementListResponse {
  unread_count: number;
  results: Announcement[];
}

export interface AnnouncementUnreadCountResponse {
  unread_count: number;
}

export interface AnnouncementReadMutationResponse {
  success: boolean;
  unread_count: number;
}

// Forward references resolved in domain.ts
import type { Player } from "./domain";
import type { Character } from "./domain";
import type { Announcement } from "./domain";
import type { ActivityTimerApiData } from "./timers";
import type { PopulationCentre } from "./domain";
import type { XpModifier } from "./domain";
import type { LoginState } from "./enums";
