import type { Meta, StoryObj } from '@storybook/react-vite';
import ProgressBar from './ProgressBar';

const meta = {
  title: 'Components/ProgressBar',
  component: ProgressBar,
  tags: ['autodocs'],
  parameters: {
    docs: {
      description: {
        component: 'Displays completion progress for timers and activities with optional labels, statuses, and paused state styling.',
      },
    },
  },
  argTypes: {
    value: { control: { type: 'number', min: 0 }, description: 'Current progress value.' },
    max: { control: { type: 'number', min: 1 }, description: 'Maximum progress value.' },
    label: { control: 'text', description: 'Text shown in or around the fill area.' },
    color: {
      control: 'select',
      options: ['default', 'warning', 'danger'],
      description: 'Semantic color variant.',
    },
    paused: { control: 'boolean', description: 'Applies paused visual treatment.' },
  },
  args: {
    value: 45,
    max: 100,
    label: '45%',
    color: 'default',
    paused: false,
  },
} satisfies Meta<typeof ProgressBar>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const Warning: Story = {
  args: {
    value: 75,
    label: 'Low time',
    color: 'warning',
  },
};

export const Paused: Story = {
  args: {
    value: 30,
    label: 'Paused',
    paused: true,
  },
};
