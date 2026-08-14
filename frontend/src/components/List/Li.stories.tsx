import type { Meta, StoryObj } from '@storybook/react-vite';
import Li from './Li';

/**
 * `Li` is the single-row primitive `List` maps over. Storied directly for
 * its own states (`isSelected`, `isHidden`, `tone`) - `List`'s stories cover
 * it in context, as a full `<ul>`.
 */
const meta: Meta<typeof Li> = {
  title: 'Shared/List/Li',
  component: Li,
  tags: ['autodocs'],
  render: (args) => (
    <ul>
      <Li {...args} />
    </ul>
  ),
  args: {
    children: 'Row content',
  },
};

export default meta;
type Story = StoryObj<typeof Li>;

export const Default: Story = {};

export const Selected: Story = {
  args: { isSelected: true },
};

export const Hidden: Story = {
  args: { isHidden: true },
};

export const PlayerTone: Story = {
  args: { tone: 'player', children: 'You finished Write docs' },
};

export const CharacterTone: Story = {
  args: { tone: 'character', children: 'Rosie finished Deliver goods' },
};
