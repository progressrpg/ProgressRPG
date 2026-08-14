import type { Meta, StoryObj } from '@storybook/react-vite';
import { expect, userEvent, within } from 'storybook/test';
import PlayerItemList from './PlayerItemList';
import type { FilterOption, SortOption } from './PlayerItemList';

/**
 * `PlayerItemList` is the generic, prop-driven list underlying
 * `CategoriesPanel`, `ProjectsPanel`, `SkillsPanel`, `TasksPanel`, and
 * `ActivitiesPanel` - it owns sorting, filtering, the edit/delete modal,
 * hover-edit affordances, and nested children, while the panel supplies the
 * item shape and callbacks. Storying it here documents most of what those
 * five panels visually do.
 */
interface DemoItem {
  id: number;
  name: string;
  detail: string;
  complete?: boolean;
}

const items: DemoItem[] = [
  { id: 1, name: 'Write docs', detail: 'Duration: 15m · 15 XP gained', complete: false },
  { id: 2, name: 'Fix login bug', detail: 'Duration: 42m · 40 XP gained', complete: true },
  { id: 3, name: 'Plan sprint', detail: 'Duration: 5m · 5 XP gained', complete: false },
];

const sortOptions: SortOption<DemoItem>[] = [
  { key: 'name', label: 'Name', compareFn: (a, b) => a.name.localeCompare(b.name) },
  { key: 'newest', label: 'Newest', compareFn: (a, b) => b.id - a.id },
];

const filterOptions: FilterOption<DemoItem>[] = [
  { key: 'all', label: 'All', predicate: () => true },
  { key: 'incomplete', label: 'Incomplete', predicate: (item) => !item.complete },
];

const meta: Meta<typeof PlayerItemList<DemoItem>> = {
  title: 'Shared/PlayerItemList',
  component: PlayerItemList,
  tags: ['autodocs'],
  args: {
    items,
    itemLabel: 'activity',
    ariaLabel: 'Activities',
    renderItemMeta: (item: DemoItem) => item.detail,
    onEdit: () => {},
  },
};

export default meta;
type Story = StoryObj<typeof PlayerItemList<DemoItem>>;

export const Default: Story = {};

/** `hoverEdit` swaps the row's click-to-open button for a persistent detail area plus a hover-revealed edit icon - used by panels where the row itself does something else on click. */
export const HoverEdit: Story = {
  args: { hoverEdit: true },
};

/** `isItemComplete`/`onToggleComplete` add a per-row checkbox, e.g. for `TasksPanel`. */
export const WithCompleteToggle: Story = {
  args: {
    isItemComplete: (item: DemoItem) => Boolean(item.complete),
    onToggleComplete: () => {},
  },
};

/** `sortOptions`/`filterOptions` render a controls bar above the list. */
export const WithSortAndFilter: Story = {
  args: { sortOptions, filterOptions },
  play: async ({ canvas }) => {
    await expect(canvas.getByRole('group', { name: 'Filter activitys' })).toBeVisible();
    await expect(canvas.getByLabelText('Sort:')).toBeVisible();
  },
};

/** `getChildren` nests an item's children directly under it (e.g. subtasks), independent of the active sort/filter. */
export const WithNestedChildren: Story = {
  args: {
    items: [
      { id: 1, name: 'Ship v1', detail: '2 subtasks', complete: false },
      { id: 2, name: 'Write changelog', detail: 'Duration: 10m', complete: false },
      { id: 3, name: 'Cut release', detail: 'Duration: 5m', complete: true },
    ],
    getChildren: (item: DemoItem) =>
      item.id === 1
        ? [
            { id: 2, name: 'Write changelog', detail: 'Duration: 10m', complete: false },
            { id: 3, name: 'Cut release', detail: 'Duration: 5m', complete: true },
          ]
        : undefined,
  },
};

/** No items - the shared empty list state (an empty `<ul>`, no placeholder copy of its own). */
export const Empty: Story = {
  args: { items: [] },
};

/** Clicking a row opens the edit modal; `onDelete` adds a Delete action with its own confirm step. */
export const EditModal: Story = {
  args: { onDelete: () => {} },
  play: async ({ canvasElement, canvas }) => {
    await userEvent.click(canvas.getByRole('button', { name: 'Open activity Write docs' }));

    const body = within(canvasElement.ownerDocument.body);
    const dialog = await body.findByRole('dialog', { name: 'Edit activity' });
    await expect(dialog).toBeVisible();
    await expect(body.getByRole('button', { name: 'Delete' })).toBeVisible();
  },
};
