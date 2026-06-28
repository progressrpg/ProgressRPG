import type { Meta, StoryObj } from '@storybook/react-vite';
import Button from './Button';

const meta = {
  title: 'Components/Button',
  component: Button,
  tags: ['autodocs'],
  parameters: {
    docs: {
      description: {
        component: 'Generic action trigger used for primary, secondary, and destructive actions. Use links only for navigation targets.',
      },
    },
  },
  argTypes: {
    variant: {
      control: 'select',
      options: ['primary', 'secondary', 'secondaryDanger', 'danger'],
      description: 'Visual style for importance and intent.',
    },
    as: {
      control: 'inline-radio',
      options: ['button', 'a'],
      description: 'Rendered element type. Use `a` with `href` for navigation.',
    },
    href: {
      control: 'text',
      description: 'Destination URL when `as` is `a`.',
    },
    disabled: {
      control: 'boolean',
      description: 'Disables interaction.',
    },
    children: {
      control: 'text',
      description: 'Visible button label.',
    },
  },
  args: {
    children: 'Save changes',
    variant: 'primary',
    as: 'button',
    disabled: false,
  },
} satisfies Meta<typeof Button>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Primary: Story = {};

export const Secondary: Story = {
  args: {
    variant: 'secondary',
    children: 'Secondary action',
  },
};

export const LinkVariant: Story = {
  args: {
    as: 'a',
    href: '#',
    children: 'Go to details',
  },
};

export const WithIcon: Story = {
  args: {
    icon: <span>⚡</span>,
    children: 'Quick start',
  },
};
