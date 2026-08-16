/**
 * Domain interfaces — shapes of the core game entities as returned by
 * the DRF serializers. Field names match the serializer output exactly.
 */

import type { CharacterActivityStatus, XpModifierScope } from "./enums";

// ---------------------------------------------------------------------------
// User (api/serializers.py — UserSerializer)
// ---------------------------------------------------------------------------

export interface User {
  email: string;
  is_confirmed: boolean;
  is_staff: boolean;
  is_superuser: boolean;
  date_of_birth: string | null;
  timezone: string;
}

// ---------------------------------------------------------------------------
// Player (users/serializers.py — PlayerSerializer)
// ---------------------------------------------------------------------------

export interface AchievementGoal {
  type: string;
  label: string;
  symbol?: string;
  tier: number;
  complete: boolean;
  color?: string;
  value: number;
  threshold: number;
  next_threshold?: number | null;
}

export interface Player {
  id: number;
  name: string;
  xp: number;
  xp_next_level: number;
  xp_modifier: number;
  level: number;
  total_time: number;
  total_activities: number;
  achievements: AchievementGoal[];
  is_premium: boolean;
  is_tester: boolean;
  has_previous_subscription: boolean;
  is_trialing: boolean;
  trial_end: string | null;
  onboarding_step: number;
  onboarding_completed: boolean;
  login_streak: number;
  unseen_tutorial_step_ids: number[];
}

export interface Announcement {
  id: number;
  title: string;
  summary: string;
  body: string;
  published_at: string | null;
  created_at: string;
  is_read: boolean;
}

// ---------------------------------------------------------------------------
// Character (character/serializers.py — CharacterSerializer)
// ---------------------------------------------------------------------------

export interface GeoJSONPoint {
  type: "Point";
  coordinates: [number, number];
}

export interface Character {
  id: number;
  name: string;
  backstory: string;
  age: number;
  sex: string;
  xp: number;
  xp_next_level: number;
  xp_modifier: number;
  level: number;
  coins: number;
  total_activities: number;
  current_activity: string | null;
  is_npc: boolean;
  can_link: boolean;
  population_centre_id: number | null;
  location: GeoJSONPoint | null;
  current_node: number | null;
  target_node: number | null;
}

// ---------------------------------------------------------------------------
// PlayerSkill (progression/serializers.py — PlayerSkillSerializer)
// ---------------------------------------------------------------------------

export interface PlayerSkill {
  id: number;
  name: string;
  description: string;
  level: number;
  created_at: string;
  last_updated: string;
  total_time: number;
  total_records: number;
  total_xp: number;
  player: number;
  is_private: boolean;
  category: number | null;
}

// ---------------------------------------------------------------------------
// Category (progression/serializers.py — CategorySerializer)
// ---------------------------------------------------------------------------

export interface Category {
  id: number;
  name: string;
  description: string;
  created_at: string;
  last_updated: string;
  total_time: number;
  total_records: number;
  total_xp: number;
  player: number;
}

// ---------------------------------------------------------------------------
// PlayerActivity (progression/serializers.py — PlayerActivitySerializer)
// ---------------------------------------------------------------------------

export interface PlayerActivity {
  id: number;
  name: string;
  description: string;
  duration: number;
  started_at: string | null;
  is_complete: boolean;
  completed_at: string | null;
  xp_gained: number | null;
  created_at: string;
  last_updated: string;
  player: number;
  group_key: string;
  is_private: boolean;
  skill: number | null;
  project: number | null;
  task: number | null;
  /** FK to the reusable Activity "type" (catalog entry), not this session's own id. */
  activity: number | null;
}

// ---------------------------------------------------------------------------
// CharacterActivity (progression/serializers.py — CharacterActivitySerializer)
// ---------------------------------------------------------------------------

export interface CharacterActivity {
  id: number;
  name: string;
  description: string;
  duration: number;
  started_at: string | null;
  is_complete: boolean;
  completed_at: string | null;
  xp_gained: number | null;
  created_at: string;
  last_updated: string;
  character: number;
  scheduled_start: string | null;
  scheduled_end: string | null;
  status: CharacterActivityStatus;
  kind: string;
}

// ---------------------------------------------------------------------------
// Project (progression/serializers.py — ProjectSerializer)
// ---------------------------------------------------------------------------

export interface Project {
  id: number;
  name: string;
  description: string;
  player: number;
  created_at: string;
  last_updated: string;
  is_complete: boolean;
  completed_at: string | null;
  total_time: number;
  total_records: number;
}

// ---------------------------------------------------------------------------
// Task (progression/serializers.py — TaskSerializer)
// ---------------------------------------------------------------------------

export interface Task {
  id: number;
  name: string;
  description: string;
  player: number;
  project: number | null;
  created_at: string;
  last_updated: string;
  is_complete: boolean;
  completed_at: string | null;
  first_completed_at: string | null;
  due_at: string | null;
  parent: number | null;
  subtask_count: number;
  total_time: number;
  total_records: number;
  last_worked_on: string | null;
}

// ---------------------------------------------------------------------------
// Note (progression/serializers.py — NoteSerializer)
// ---------------------------------------------------------------------------

export interface Note {
  id: number;
  title: string;
  body: string;
  player: number;
  task: number | null;
  activity: number | null;
  created_at: string;
  last_updated: string;
}

// ---------------------------------------------------------------------------
// XpModifier (gameplay/serializers.py — XpModifierSerializer)
// ---------------------------------------------------------------------------

export interface XpModifier {
  id: number;
  scope: XpModifierScope;
  key: string;
  multiplier: number;
  starts_at: string;
  ends_at: string | null;
  is_active: boolean;
}

// ---------------------------------------------------------------------------
// PopulationCentre (locations/serializers.py — PopulationCentreSerializer)
// ---------------------------------------------------------------------------

export interface Building {
  id: number;
  name: string;
  description: string;
  population_centre_id: number;
  building_type: string;
}

export interface PopulationCentre {
  id: number;
  name: string;
  description: string;
  village_points: number;
  progress: number;
  state: string;
  residents: Character[];
  buildings: Building[];
}

// ---------------------------------------------------------------------------
// TutorialStep (users/serializers.py — TutorialStepSerializer)
// ---------------------------------------------------------------------------

export interface TutorialStep {
  id: number;
  order: number;
  title: string;
  body: string;
  image_url: string | null;
  alt_text: string;
  youtube_url: string | null;
}
