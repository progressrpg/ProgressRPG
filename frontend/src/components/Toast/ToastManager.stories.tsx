import * as RadixToast from '@radix-ui/react-toast';
import type { Meta, StoryObj } from '@storybook/react-vite';
import { expect, waitFor, within } from 'storybook/test';
import ToastManager from './ToastManager';

/**
 * `ToastManager` renders a `messages[]` prop as Radix `Toast.Root`s plus the
 * shared `Toast.Viewport`. It must be mounted under a Radix `Toast.Provider`
 * (normally supplied by `ToastContext`) - the story provides one directly.
 */
const meta: Meta<typeof ToastManager> = {
  title: 'Shared/ToastManager',
  component: ToastManager,
  tags: ['autodocs'],
  decorators: [
    (Story) => (
      <RadixToast.Provider>
        <Story />
      </RadixToast.Provider>
    ),
  ],
  args: {
    onDismiss: () => {},
  },
};

export default meta;
type Story = StoryObj<typeof ToastManager>;

export const Default: Story = {
  args: {
    messages: [{ id: '1', message: 'Task saved.' }],
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    // .toast[data-state='open'] runs a real 0.25s fadeInUp animation
    // starting at opacity: 0, so the toast isn't `toBeVisible()` on the
    // very first frame after mount - wait for the animation to progress.
    await waitFor(() => {
      expect(canvas.getByText('Task saved.')).toBeVisible();
    });
  },
};

export const Multiple: Story = {
  args: {
    messages: [
      { id: '1', message: 'Task saved.' },
      { id: '2', message: 'Activity logged - 15 XP gained.' },
      { id: '3', message: 'Level up! You reached level 6.' },
    ],
  },
};

export const Empty: Story = {
  args: { messages: [] },
};
