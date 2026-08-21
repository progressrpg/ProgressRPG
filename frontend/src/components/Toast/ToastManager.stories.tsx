import { ToastProvider } from 'tamagui';
import type { Meta, StoryObj } from '@storybook/react-vite';
import { expect, waitFor, within } from 'storybook/test';
import ToastManager from './ToastManager';

/**
 * `ToastManager` renders a `messages[]` prop as Tamagui `Toast`s plus the
 * shared `ToastViewport` (#581). It must be mounted under a Tamagui
 * `ToastProvider` (normally supplied by `ToastContext`, alongside the global
 * `TamaguiProvider` from `.storybook/preview.tsx`) - the story provides one
 * directly.
 */
const meta: Meta<typeof ToastManager> = {
  title: 'Shared/ToastManager',
  component: ToastManager,
  tags: ['autodocs'],
  decorators: [
    (Story) => (
      <ToastProvider>
        <Story />
      </ToastProvider>
    ),
  ],
  args: {
    onDismiss: () => {},
  },
  parameters: {
    a11y: {
      config: {
        // `ToastViewport` (Tamagui, ported from Radix's Toast) renders two
        // invisible `FocusProxy` sentinels (aria-hidden + tabIndex=0) that
        // detect Tab focus entering/exiting the viewport so it can redirect
        // to the first/last toast - the same intentional pattern
        // @radix-ui/react-toast uses upstream. aria-hidden-focus can't tell
        // "hidden from screen readers but a deliberate keyboard-only
        // sentinel" from a real bug, so it's disabled here rather than
        // worked around.
        rules: [{ id: 'aria-hidden-focus', enabled: false }],
      },
    },
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
