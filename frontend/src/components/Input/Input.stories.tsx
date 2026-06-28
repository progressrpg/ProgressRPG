import type { Meta, StoryObj } from '@storybook/react-vite';
import { useState } from 'react';
import type { ComponentProps } from 'react';
import Input from './Input';

function ControlledInput(args: ComponentProps<typeof Input>) {
  const [value, setValue] = useState(args.value ?? '');

  return (
    <Input
      {...args}
      value={value}
      onChange={(next) => setValue(String(next))}
    />
  );
}

const meta = {
  title: 'Components/Input',
  component: Input,
  tags: ['autodocs'],
  parameters: {
    docs: {
      description: {
        component: 'Form input wrapper with labels, help/error messaging, checkbox support, and password visibility toggle.',
      },
    },
  },
  argTypes: {
    label: { description: 'Field label linked to the input id.' },
    type: {
      control: 'select',
      options: ['text', 'email', 'password', 'checkbox'],
      description: 'Input field type.',
    },
    helpText: { description: 'Supporting copy shown when there is no error.' },
    error: { description: 'Validation message and error state.' },
    required: { control: 'boolean', description: 'Adds required semantics and indicator.' },
    disabled: { control: 'boolean', description: 'Disables user interaction.' },
  },
  args: {
    id: 'storybook-input',
    label: 'Task name',
    type: 'text',
    value: '',
    placeholder: 'Enter a task',
    helpText: 'Use a short and clear name.',
    required: false,
    disabled: false,
  },
  render: (args) => <ControlledInput {...args} />,
} satisfies Meta<typeof Input>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Text: Story = {};

export const Password: Story = {
  args: {
    id: 'storybook-password',
    label: 'Password',
    type: 'password',
    value: 'secret123',
    helpText: 'Use at least 8 characters.',
  },
};

export const ErrorState: Story = {
  args: {
    id: 'storybook-error',
    error: 'This field is required.',
    value: '',
  },
};
