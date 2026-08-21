import type { Meta, StoryObj } from '@storybook/react-vite';
import { expect, within } from 'storybook/test';
import Modal from './Modal';
import Button from '../Button/Button';

/**
 * `Modal` is an always-open Tamagui `Dialog` (#582) intended to be
 * conditionally mounted by the parent (mount when shown, unmount on
 * `onClose`). Use it for informational overlays; for confirm/destructive
 * prompts use `AlertDialog` instead.
 */
const meta: Meta<typeof Modal> = {
  title: 'Shared/Modal',
  component: Modal,
  tags: ['autodocs'],
  args: {
    title: 'Modal title',
    children: <p>Modal body content goes here.</p>,
  },
};

export default meta;
type Story = StoryObj<typeof Modal>;

export const Default: Story = {
  play: async ({ canvasElement }) => {
    // Modal renders via a Tamagui Portal into document.body, outside the canvas.
    const body = within(canvasElement.ownerDocument.body);
    const dialog = await body.findByRole('dialog', { name: 'Modal title' });
    await expect(dialog).toBeVisible();
  },
};

export const WithFooter: Story = {
  args: {
    footer: (
      <>
        <Button variant="secondary">Cancel</Button>
        <Button>Save</Button>
      </>
    ),
  },
};

/** `onBack` renders a back button in the header, useful for multi-step flows. */
export const WithBackButton: Story = {
  args: {
    onBack: () => {},
    backLabel: 'Back',
  },
};

export const Large: Story = {
  args: { size: 'lg' },
};
