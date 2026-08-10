// src/featureFlags.ts
import type { FeatureFlagKey, FeatureFlagValue } from "./types";

const featureFlags: Record<FeatureFlagKey, FeatureFlagValue> = {
  // Each flag is an array of groups that have access.
  // Groups: 'all' | 'premium' | 'testers'
  // Empty array = disabled for everyone.
  tasksFeature: ['testers'],
  categoriesFeature: [],
  skillsFeature: [],
  notesFeature: ['testers'],
  projectsFeature: [],
  toastsFeature: [],
  announcements: ['testers'],
  onlinePlayerCount: ['testers'],
  unified_homepage: [],
  results_mode: [],
  map: ['testers'],
  dailyGoalsBadge: ['all'],
};

export default featureFlags;
