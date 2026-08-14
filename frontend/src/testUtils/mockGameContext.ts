import type { GameContextValue } from '../context/gameContext';

/**
 * Minimal `GameContextValue` covering only what story-ready components
 * actually read (currently `player`, via `useFeatureFlag`). The rest are
 * stubs so the object satisfies the full interface without pulling in
 * `GameProvider`'s real bootstrap/fetch logic - extend as more components
 * that read other fields get storied.
 *
 * Used by Storybook stories that mount `GameContext.Provider` directly
 * (`.storybook/decorators/withGameContext.tsx`, `EntitySearchInput.stories.tsx`).
 */
export const mockGameContextValue: GameContextValue = {
  player: null,
  setPlayer: () => {},
  character: null,
  setCharacter: () => {},
  xpMods: [],
  setXpMods: () => {},
  fetchPlayerAndCharacter: async () => {},
  activityTimer: {
    status: 'empty',
    elapsed: 0,
    duration: 0,
    limitSeconds: null,
    limitReached: false,
    autoStopCompletion: null,
    currentActivity: null,
    startActivity: async () => null,
    labelActivity: async () => null,
    stop: async () => null,
    loadFromServer: () => {},
    clearAutoStopCompletion: () => {},
  },
  playerActivities: [],
  characterActivities: [],
  fetchActivities: async () => {},
  fetchCharacterCurrent: async () => null,
  characterCurrentActivity: null,
  setCharacterCurrentActivity: () => {},
  populationCentre: null,
  fetchPopulationCentre: async () => {
    throw new Error('fetchPopulationCentre is not mocked in Storybook');
  },
  loginState: 'none',
  loginStreak: 0,
  loginEventAt: null,
  loginRewardXp: 0,
  announcementUnreadCount: 0,
  setAnnouncementUnreadCount: () => {},
  loading: false,
  buildNumber: false,
  freeTimerLimitSeconds: 1800,
  gameSettings: null,
  initialOnlineCount: 0,
};
