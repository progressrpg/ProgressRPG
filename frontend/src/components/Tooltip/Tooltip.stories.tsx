import type { Meta, StoryObj } from '@storybook/react-vite';
import { expect, within } from 'storybook/test';
import Tooltip from './Tooltip';
import Button from '../Button/Button';

/**
 * `Tooltip` wraps a single focusable trigger element and shows supplementary
 * content on click/tap or focus via Radix — hover never opens it, on either
 * desktop or mobile (see #568). Clicking/tapping the trigger again, clicking
 * anywhere else, or pressing Escape closes it. It must be nested under a
 * `TooltipProvider` (mounted once near the app root, and globally in
 * .storybook/preview.tsx). Use tooltips only for supplementary context -
 * essential information must remain available without clicking or focusing.
 */
const meta: Meta<typeof Tooltip> = {
  title: 'Shared/Tooltip',
  component: Tooltip,
  tags: ['autodocs'],
  args: {
    content: 'Additional context shown on click/tap or focus',
    placement: 'top',
  },
};

export default meta;
type Story = StoryObj<typeof Tooltip>;

export const Default: Story = {
  render: (args) => (
    <Tooltip {...args}>
      <Button>Click or focus me</Button>
    </Tooltip>
  ),
  play: async ({ canvas, userEvent, canvasElement }) => {
    const trigger = canvas.getByRole('button', { name: 'Click or focus me' });
    await userEvent.tab();
    await expect(trigger).toHaveFocus();
    // Tooltip content renders via a Radix Portal into document.body.
    const tooltip = await within(canvasElement.ownerDocument.body).findByRole('tooltip');
    await expect(tooltip).toHaveTextContent('Additional context shown on click/tap or focus');
  },
};

export const Placements: Story = {
  render: (args) => (
    <div style={{ display: 'flex', gap: '2rem', padding: '3rem' }}>
      {(['top', 'right', 'bottom', 'left'] as const).map((placement) => (
        <Tooltip key={placement} {...args} placement={placement} content={`Placement: ${placement}`}>
          <Button>{placement}</Button>
        </Tooltip>
      ))}
    </div>
  ),
};

/** When `disabled` (or `content` is empty), the trigger renders with no tooltip wiring. */
export const Disabled: Story = {
  render: (args) => (
    <Tooltip {...args} disabled>
      <Button>No tooltip</Button>
    </Tooltip>
  ),
};
