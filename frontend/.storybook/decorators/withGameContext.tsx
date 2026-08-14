import type { Decorator } from '@storybook/react-vite';
import { GameContext } from '../../src/context/gameContext';
import { mockGameContextValue } from '../../src/testUtils/mockGameContext';

/**
 * Wraps a story in `GameContext` with `mockGameContextValue`, for components
 * that read `useGame()` (directly, or transitively via `useFeatureFlag`)
 * outside of a real game session.
 */
export const withGameContext: Decorator = (Story) => (
  <GameContext.Provider value={mockGameContextValue}>
    <Story />
  </GameContext.Provider>
);
