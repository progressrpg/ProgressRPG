import type { Meta, StoryObj } from '@storybook/react-vite';
import { expect, within } from 'storybook/test';
import DetailCard from './DetailCard';

/**
 * `DetailCard` is the entity-agnostic shell for the map's second level of
 * progressive disclosure (Map -> tooltip -> click -> DetailCard). It only
 * provides layout (title/close/content area, responsive mobile sheet vs.
 * desktop centered card) via `DetailSurface` - entity-specific content
 * (`CharacterDetail`, `BuildingDetail`, ...) is passed as `children`.
 */
const meta: Meta<typeof DetailCard> = {
  title: 'Shared/DetailCard',
  component: DetailCard,
  tags: ['autodocs'],
  // Renders via a Radix Portal into document.body - escapes the story
  // canvas with inline docs rendering, so use an iframe like AlertDialog.
  parameters: {
    docs: {
      story: { inline: false, iframeHeight: 320 },
    },
  },
  args: {
    open: true,
    title: 'Alice',
    onClose: () => {},
    children: <p>Entity-specific content goes here.</p>,
  },
};

export default meta;
type Story = StoryObj<typeof DetailCard>;

export const Default: Story = {
  play: async ({ canvasElement }) => {
    const body = within(canvasElement.ownerDocument.body);
    const dialog = await body.findByRole('dialog', { name: 'Alice' });
    await expect(dialog).toBeVisible();
    await expect(body.getByRole('button', { name: 'Close' })).toBeVisible();
  },
};

export const WithLongerContent: Story = {
  args: {
    title: 'Rose Cottage',
    children: (
      <>
        <p>House</p>
        <p>Residents: 4</p>
        <ul>
          <li>Alice (idle)</li>
          <li>Thomas (delivering goods to neighbours)</li>
          <li>Emily (idle)</li>
          <li>James (idle)</li>
        </ul>
      </>
    ),
  },
};
