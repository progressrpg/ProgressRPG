import { useState } from 'react';
import type { Meta, StoryObj } from '@storybook/react-vite';
import { expect, userEvent } from 'storybook/test';
import ModeSwitcher from './ModeSwitcher';
import type { ModeOption } from './ModeSwitcher';

/**
 * `ModeSwitcher` is a `radiogroup` of chips (e.g. Tasks/Activities panel
 * mode). Fully generic over `modes`/`activeKey`/`onSelect`; arrow keys move
 * (and select) between options, Home/End jump to the first/last.
 */
const modes: ModeOption[] = [
  { key: 'tasks', label: 'Tasks' },
  { key: 'activities', label: 'Activities' },
  { key: 'skills', label: 'Skills' },
];

const meta: Meta<typeof ModeSwitcher> = {
  title: 'Shared/ModeSwitcher',
  component: ModeSwitcher,
  tags: ['autodocs'],
  args: {
    modes,
    activeKey: 'tasks',
    ariaLabel: 'View mode',
  },
};

export default meta;
type Story = StoryObj<typeof ModeSwitcher>;

export const Default: Story = {
  render: (args) => {
    function Wrapper() {
      const [activeKey, setActiveKey] = useState(args.activeKey);
      return <ModeSwitcher {...args} activeKey={activeKey} onSelect={setActiveKey} />;
    }
    return <Wrapper />;
  },
  play: async ({ canvas }) => {
    const activities = canvas.getByRole('radio', { name: 'Activities' });
    await userEvent.click(activities);
    await expect(activities).toHaveAttribute('aria-checked', 'true');
  },
};
