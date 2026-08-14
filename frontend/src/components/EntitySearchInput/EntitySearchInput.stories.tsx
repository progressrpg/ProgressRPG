import { useState } from 'react';
import type { Meta, StoryObj } from '@storybook/react-vite';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { expect, userEvent, waitFor, within } from 'storybook/test';
import EntitySearchInput from './EntitySearchInput';
import { GameContext } from '../../context/gameContext';
import { mockGameContextValue } from '../../testUtils/mockGameContext';

/**
 * `EntitySearchInput` is a fuzzy-search combobox over the player's past
 * activities/tasks (`useEntitySearchCache`, a TanStack Query hook that in
 * turn calls `useFeatureFlag` -> `useGame()`). The story seeds the cache's
 * query directly and supplies a mock `GameContext` so it renders without a
 * real API or game session - see `.storybook/decorators/`.
 */
const entities = [
  { id: 'a1', name: 'Wash dishes', taskId: null, completedAt: null, source: 'activity', isOptimistic: false, frequency: 4 },
  { id: 'a2', name: 'Write report', taskId: null, completedAt: null, source: 'activity', isOptimistic: false, frequency: 2 },
  { id: 't1', name: 'Write tests', taskId: 12, completedAt: null, source: 'task', isOptimistic: false, frequency: 0 },
];

function withSeededCache(Story: () => React.ReactElement) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  queryClient.setQueryData(['entity-search', 'activity'], entities);
  queryClient.setQueryData(['appConfig'], { feature_flags: {} });

  return (
    <QueryClientProvider client={queryClient}>
      <GameContext.Provider value={mockGameContextValue}>
        <Story />
      </GameContext.Provider>
    </QueryClientProvider>
  );
}

const meta: Meta<typeof EntitySearchInput> = {
  title: 'Shared/EntitySearchInput',
  component: EntitySearchInput,
  tags: ['autodocs'],
  decorators: [withSeededCache],
  args: {
    type: 'activity',
    ariaLabel: 'Activity name',
    placeholder: 'What are you working on?',
  },
};

export default meta;
type Story = StoryObj<typeof EntitySearchInput>;

function ControlledInput(props: Partial<React.ComponentProps<typeof EntitySearchInput>>) {
  const [value, setValue] = useState(props.value ?? '');
  return <EntitySearchInput {...(props as React.ComponentProps<typeof EntitySearchInput>)} value={value} onChange={setValue} />;
}

export const Default: Story = {
  render: (args) => <ControlledInput {...args} />,
};

/** Typing surfaces matching activities/tasks in a dropdown, grouped by source when both are present. */
export const WithSuggestions: Story = {
  render: (args) => <ControlledInput {...args} />,
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.type(canvas.getByRole('combobox'), 'write');

    await waitFor(async () => {
      await expect(canvas.getByRole('listbox')).toBeVisible();
    });
    await expect(canvas.getByRole('option', { name: 'Write tests' })).toBeVisible();
    await expect(canvas.getByRole('option', { name: 'Write report' })).toBeVisible();
  },
};

/** `alwaysOpen` keeps the dropdown mounted regardless of focus (persistent list mode), falling back to `emptyMessage` when there are no rows. */
export const AlwaysOpenEmpty: Story = {
  args: {
    alwaysOpen: true,
    emptyMessage: 'No recent activities yet.',
    defaultResults: [],
  },
  render: (args) => <ControlledInput {...args} />,
};

export const Disabled: Story = {
  args: { disabled: true, value: 'Timer running...' },
};
