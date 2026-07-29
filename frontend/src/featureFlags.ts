// src/featureFlags.ts
import type { FeatureFlagKey, FeatureFlagValue } from "./types";

const featureFlags: Record<FeatureFlagKey, FeatureFlagValue> = {
  // Each flag is an array of groups that have access.
  // Groups: 'all' | 'premium' | 'testers'
  // Empty array = disabled for everyone.
  activityList: ['all'],
  tasksFeature: ['testers'],
  categoriesFeature: [],
  skillsFeature: [],
  projectsFeature: [],
  toastsFeature: [],
  announcements: ['testers'],
  onlinePlayerCount: ['testers'],
  unified_homepage: [],
  map: ['testers'],
};

export default featureFlags;
