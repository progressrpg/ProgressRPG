import type { Meta, StoryObj } from '@storybook/react-vite';
import { expect, within } from 'storybook/test';
import AlertDialog from './AlertDialog';

/**
 * `AlertDialog` interrupts the user with a confirm/destructive prompt that
 * requires an explicit decision before continuing (Tamagui `AlertDialog`
 * under the hood, #582). Use it in place of `window.confirm`. For
 * non-blocking informational overlays, use `Modal`.
 */
const meta: Meta<typeof AlertDialog> = {
  title: 'Shared/AlertDialog',
  component: AlertDialog,
  tags: ['autodocs'],
  // AlertDialog renders via a Tamagui Portal into document.body. With inline
  // docs rendering that portal escapes the story canvas and covers the whole
  // docs page, so render each story in its own iframe instead.
  parameters: {
    docs: {
      story: { inline: false, iframeHeight: 260 },
    },
  },
  args: {
    open: true,
    title: 'Delete this activity?',
    description: 'This action cannot be undone.',
    onConfirm: () => {},
    onCancel: () => {},
  },
};

export default meta;
type Story = StoryObj<typeof AlertDialog>;

export const Default: Story = {};

export const Destructive: Story = {
  args: {
    variant: 'destructive',
    confirmLabel: 'Delete',
  },
  play: async ({ canvasElement }) => {
    // AlertDialog renders via a Tamagui Portal into document.body, outside the canvas.
    const body = within(canvasElement.ownerDocument.body);
    const dialog = await body.findByRole('alertdialog', { name: 'Delete this activity?' });
    await expect(dialog).toBeVisible();
    await expect(body.getByRole('button', { name: 'Delete' })).toBeVisible();
  },
};

export const CustomLabels: Story = {
  args: {
    title: 'Discard changes?',
    description: "You'll lose any unsaved edits.",
    confirmLabel: 'Discard',
    cancelLabel: 'Keep editing',
  },
};
