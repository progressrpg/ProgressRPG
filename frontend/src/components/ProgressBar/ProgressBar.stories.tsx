import type { Meta, StoryObj } from '@storybook/react-vite';
import { expect } from 'storybook/test';
import ProgressBar from './ProgressBar';

/**
 * `ProgressBar` shows `value`/`max` as a filled track (Tamagui `Progress`
 * under the hood, unstyled so `ProgressBar.module.scss` stays the sole
 * source of visual truth). The `label` renders inside the fill once
 * there's room, otherwise it moves outside so it stays readable.
 */
const meta: Meta<typeof ProgressBar> = {
  title: 'Shared/ProgressBar',
  component: ProgressBar,
  tags: ['autodocs'],
  argTypes: {
    color: {
      control: 'select',
      options: ['default', 'warning', 'danger'],
    },
  },
  args: {
    value: 40,
    max: 100,
  },
};

export default meta;
type Story = StoryObj<typeof ProgressBar>;

export const Default: Story = {};

export const WithLabel: Story = {
  args: { label: '40 / 100 XP' },
};

export const NearComplete: Story = {
  args: { value: 92, label: '92 / 100 XP' },
  play: async ({ canvas }) => {
    const track = canvas.getByRole('progressbar', { name: '92 / 100 XP' });
    await expect(track).toHaveAttribute('aria-valuenow', '92');
    await expect(track).toHaveAttribute('aria-valuemax', '100');
  },
};

export const Warning: Story = {
  args: { value: 70, color: 'warning', label: '70%' },
};

export const Danger: Story = {
  args: { value: 15, color: 'danger', label: '15%' },
};

export const Paused: Story = {
  args: { value: 40, paused: true, label: 'Paused' },
};
