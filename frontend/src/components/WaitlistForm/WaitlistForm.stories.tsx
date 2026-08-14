import type { Meta, StoryObj } from '@storybook/react-vite';
import { expect, within } from 'storybook/test';
import WaitlistForm from './WaitlistForm';

/**
 * `WaitlistForm` is a single-field email form backed by `useWaitlistJoin`,
 * which posts to the real waitlist API - the story only exercises the idle,
 * pre-submission render (an interactive Storybook play test would hit a
 * live endpoint).
 */
const meta: Meta<typeof WaitlistForm> = {
  title: 'Shared/WaitlistForm',
  component: WaitlistForm,
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj<typeof WaitlistForm>;

export const Default: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(canvas.getByRole('heading', { name: 'Join the Waitlist' })).toBeVisible();
    await expect(canvas.getByLabelText('Email:')).toBeVisible();
  },
};

export const CustomTitle: Story = {
  args: { title: 'Be first in line' },
};
