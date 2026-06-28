import type { Meta, StoryObj } from '@storybook/react-vite';
import Button from '../Button/Button';
import Modal from './Modal';

const meta = {
  title: 'Components/Modal',
  component: Modal,
  tags: ['autodocs'],
  parameters: {
    docs: {
      description: {
        component: 'Accessible dialog with focus trapping, escape handling, backdrop close, and optional back/footer sections.',
      },
    },
    layout: 'fullscreen',
  },
  argTypes: {
    title: { description: 'Modal heading text.' },
    onClose: { description: 'Called when close action is triggered.' },
    onBack: { description: 'Optional back action displayed in the header.' },
    backLabel: { description: 'Accessible text for the back button.' },
    size: {
      control: 'select',
      options: [undefined, 'sm', 'lg'],
      description: 'Width preset for the dialog.',
    },
    children: { control: false, description: 'Main modal content.' },
    footer: { control: false, description: 'Optional footer actions.' },
  },
  args: {
    title: 'Session settings',
    onClose: () => {},
    children: 'Adjust your focus session and start when ready.',
  },
} satisfies Meta<typeof Modal>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Basic: Story = {};

export const WithBackAndFooter: Story = {
  args: {
    onBack: () => {},
    backLabel: 'Choose mode',
    footer: (
      <>
        <Button variant="secondary">Cancel</Button>
        <Button>Start session</Button>
      </>
    ),
  },
};
