import type { Meta, StoryObj } from '@storybook/react-vite';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { expect, within } from 'storybook/test';
import TutorialModal from './TutorialModal';
import type { TutorialStep } from '../../types';

/**
 * `TutorialModal` walks through `TutorialStep`s fetched via `useTutorialSteps`
 * (a TanStack Query hook - see `withQueryClient` in `.storybook/preview.tsx`).
 * Each story seeds the `["tutorial-steps"]` query directly with
 * `queryClient.setQueryData` so the modal renders without a real API call.
 */
const steps: TutorialStep[] = [
  {
    id: 1,
    order: 1,
    title: 'Welcome to Progress RPG',
    body: 'Your character levels up as you complete real-world tasks and activities.',
    image_url: null,
    alt_text: '',
    youtube_url: null,
  },
  {
    id: 2,
    order: 2,
    title: 'Start a timer',
    body: 'Type what you\'re working on and hit Start - XP accrues while the timer runs.',
    image_url: null,
    alt_text: '',
    youtube_url: 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
  },
  {
    id: 3,
    order: 3,
    title: "You're all set",
    body: 'That\'s the core loop. Explore the map to see other characters at work.',
    image_url: null,
    alt_text: '',
    youtube_url: null,
  },
];

/** Seeds `["tutorial-steps"]` with `data` before the story renders. */
function withSeededSteps(data: TutorialStep[]) {
  return (Story: () => React.ReactElement) => {
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    queryClient.setQueryData(['tutorial-steps'], data);
    return (
      <QueryClientProvider client={queryClient}>
        <Story />
      </QueryClientProvider>
    );
  };
}

const meta: Meta<typeof TutorialModal> = {
  title: 'Shared/TutorialModal',
  component: TutorialModal,
  tags: ['autodocs'],
  parameters: {
    docs: {
      story: { inline: false, iframeHeight: 420 },
    },
  },
  args: {
    onClose: () => {},
  },
  decorators: [withSeededSteps(steps)],
};

export default meta;
type Story = StoryObj<typeof TutorialModal>;

export const Default: Story = {
  play: async ({ canvasElement }) => {
    const body = within(canvasElement.ownerDocument.body);
    await expect(await body.findByRole('dialog', { name: 'Welcome to Progress RPG' })).toBeVisible();
    await expect(body.getByText('1 / 3')).toBeVisible();
  },
};

/** `startAtStepId` opens directly on a later step, e.g. re-opening from a "Learn more" link elsewhere in the app. */
export const StartAtLaterStep: Story = {
  args: { startAtStepId: 2 },
};

export const NoSteps: Story = {
  decorators: [withSeededSteps([])],
};
