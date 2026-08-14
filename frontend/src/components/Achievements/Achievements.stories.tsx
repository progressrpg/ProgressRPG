import type { Meta, StoryObj } from '@storybook/react-vite';
import Achievements from './Achievements';

/**
 * `Achievements` renders a grid of achievement badges from a plain
 * `achievements[]` prop - tier colour, progress bar, and the "time" vs.
 * count value formatting are all derived from each achievement's fields.
 */
const meta: Meta<typeof Achievements> = {
  title: 'Shared/Achievements',
  component: Achievements,
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj<typeof Achievements>;

export const Default: Story = {
  args: {
    achievements: [
      {
        type: 'tasks_completed',
        label: 'Task Master',
        symbol: '✅',
        tier: 1,
        complete: false,
        color: 'grey',
        value: 12,
        threshold: 25,
      },
      {
        type: 'tasks_completed',
        label: 'Task Master',
        symbol: '✅',
        tier: 2,
        complete: true,
        color: 'green',
        value: 50,
        threshold: 50,
      },
      {
        type: 'time',
        label: 'Time Invested',
        symbol: '⏱️',
        tier: 3,
        complete: false,
        color: 'blue',
        value: 5400,
        threshold: 36000,
      },
      {
        type: 'streak',
        label: 'Consistency',
        symbol: '🔥',
        tier: 4,
        complete: false,
        color: 'purple',
        value: 8,
        threshold: 30,
      },
      {
        type: 'level',
        label: 'Levelled Up',
        symbol: '⭐',
        tier: 5,
        complete: true,
        color: 'gold',
        value: 20,
        threshold: 20,
      },
    ],
  },
};

/** Every tier colour Achievements knows about (`grey`/`green`/`blue`/`purple`/`gold`), all mid-progress. */
export const AllTiers: Story = {
  args: {
    achievements: (['grey', 'green', 'blue', 'purple', 'gold'] as const).map((color, i) => ({
      type: 'tasks_completed',
      label: `Tier ${i + 1}`,
      symbol: '🏅',
      tier: i + 1,
      complete: false,
      color,
      value: (i + 1) * 5,
      threshold: 50,
    })),
  },
};

export const Empty: Story = {
  args: { achievements: [] },
};
