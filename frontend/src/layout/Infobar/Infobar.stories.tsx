import type { Meta, StoryObj } from '@storybook/react-vite';
import { expect, within } from 'storybook/test';
import Infobar from './Infobar';
import { GameContext } from '../../context/gameContext';
import { mockGameContextValue } from '../../testUtils/mockGameContext';
import type { Player } from '../../types';

/**
 * `Infobar` reads `player`/`loading` off `useGame()` - see
 * `.storybook/decorators/withGameContext.tsx` for the shared mock, extended
 * here per story with a concrete `player`.
 */
const demoPlayer: Player = {
  id: 1,
  name: 'Alex',
  xp: 340,
  xp_next_level: 500,
  xp_modifier: 1,
  level: 7,
  total_time: 54000,
  total_activities: 42,
  achievements: [
    { type: 'tasks_completed', label: 'Task Master', symbol: '✅', tier: 2, complete: true, color: 'green', value: 50, threshold: 50 },
    { type: 'streak', label: 'Consistency', symbol: '🔥', tier: 1, complete: false, color: 'grey', value: 8, threshold: 30 },
  ],
  is_premium: false,
  is_tester: false,
  has_previous_subscription: false,
  is_trialing: false,
  trial_end: null,
  onboarding_step: 5,
  onboarding_completed: true,
  login_streak: 8,
  unseen_tutorial_step_ids: [],
  progressive_unlocks: { infobar: true, library: true, map: true },
};

function withPlayer(player: Player | null, loading = false) {
  return (Story: () => React.ReactElement) => (
    <GameContext.Provider value={{ ...mockGameContextValue, player, loading }}>
      <Story />
    </GameContext.Provider>
  );
}

const meta: Meta<typeof Infobar> = {
  title: 'Layout/Infobar',
  component: Infobar,
  tags: ['autodocs'],
  decorators: [withPlayer(demoPlayer)],
};

export default meta;
type Story = StoryObj<typeof Infobar>;

export const Default: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(canvas.getByText('Alex')).toBeVisible();
    await expect(canvas.getByText('Level 7')).toBeVisible();
  },
};

export const PremiumPlayer: Story = {
  decorators: [withPlayer({ ...demoPlayer, is_premium: true })],
};

export const Loading: Story = {
  decorators: [withPlayer(null, true)],
};

/** Renders nothing once loaded without a player (e.g. between logout and redirect). */
export const NoPlayer: Story = {
  decorators: [withPlayer(null, false)],
};
