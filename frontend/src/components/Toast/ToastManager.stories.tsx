import * as RadixToast from '@radix-ui/react-toast';
import type { Meta, StoryObj } from '@storybook/react-vite';
import { expect, within } from 'storybook/test';
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
    await expect(canvas.getByText('Task saved.')).toBeVisible();
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
