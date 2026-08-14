import type { Meta, StoryObj } from '@storybook/react-vite';
import { expect, within } from 'storybook/test';
import BackToTopButton from './BackToTopButton';

/**
 * `BackToTopButton` is a fixed-position button that smooth-scrolls the page
 * to the top (instantly, if the user prefers reduced motion). No props -
 * visibility/positioning is left to the page that mounts it.
 */
const meta: Meta<typeof BackToTopButton> = {
  title: 'Shared/BackToTopButton',
  component: BackToTopButton,
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj<typeof BackToTopButton>;

export const Default: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(canvas.getByRole('button', { name: 'Back to top' })).toBeVisible();
  },
};
