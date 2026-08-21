import { useState } from 'react';
import type { Meta, StoryObj } from '@storybook/react-vite';
import { expect, userEvent } from 'storybook/test';
import List from './List';

/**
 * `List` renders a `<ul>` of `Li` rows and underlies `PlayerItemList` (which
 * adds sort/filter/edit-modal behaviour on top). On its own it handles
 * selection, hover/compact styling, and per-item tone (e.g. distinguishing
 * player vs. character rows in an activity feed).
 */
interface DemoItem {
  id: string;
  name: string;
  player?: unknown;
  character?: unknown;
  isHidden?: boolean;
}

const items: DemoItem[] = [
  { id: '1', name: 'Alice' },
  { id: '2', name: 'Bob' },
  { id: '3', name: 'Carol' },
];

const meta: Meta<typeof List<DemoItem>> = {
  title: 'Shared/List',
  component: List,
  tags: ['autodocs'],
  args: {
    items,
    ariaLabel: 'Names',
    renderItem: (item) => item.name,
  },
};

export default meta;
type Story = StoryObj<typeof List<DemoItem>>;

export const Default: Story = {};

export const CanHover: Story = {
  args: { canHover: true },
};

export const Compact: Story = {
  args: { compact: true },
};

/** A hidden item (e.g. a deep-link placeholder) stays in the DOM but is visually suppressed via `isHidden`. */
export const WithHiddenItem: Story = {
  args: {
    items: [...items, { id: '4', name: 'Dave', isHidden: true }],
  },
};

/** `itemTone`/`getItemTone` colour rows by origin - e.g. an activity feed mixing player and character entries. */
export const MixedTone: Story = {
  args: {
    items: [
      { id: '1', name: 'You finished Write docs', player: {} },
      { id: '2', name: 'Rosie finished Deliver goods', character: {} },
    ],
  },
};

/** `canSelect` renders a `listbox`/`option` pair with keyboard (Enter/Space) activation instead of a plain list. */
export const Selectable: Story = {
  render: (args) => {
    function Wrapper() {
      const [selectedItem, setSelectedItem] = useState<DemoItem | null>(null);
      return <List {...args} selectedItem={selectedItem} onSelect={setSelectedItem} canSelect />;
    }
    return <Wrapper />;
  },
  play: async ({ canvas }) => {
    const option = canvas.getByRole('option', { name: 'Bob' });
    await userEvent.click(option);
    await expect(option).toHaveAttribute('aria-selected', 'true');
  },
};
