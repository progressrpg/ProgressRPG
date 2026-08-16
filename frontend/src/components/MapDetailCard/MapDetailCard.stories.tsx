import type { Meta, StoryObj } from '@storybook/react-vite';
import { expect, within } from 'storybook/test';
import MapDetailCard from './MapDetailCard';

/**
 * `MapDetailCard` is the map's docked side-panel variant of DetailCard's
 * header/content layout - a click on a character/building stays open and
 * browsable alongside the map instead of covering it. Non-modal (no dimming
 * overlay, the map underneath stays interactive), narrower than DetailCard,
 * and positions relative to the map itself (via the `container` prop)
 * rather than the viewport.
 */
const meta: Meta<typeof MapDetailCard> = {
  title: 'Shared/MapDetailCard',
  component: MapDetailCard,
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
    title: 'Rose Cottage',
    onClose: () => {},
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

export default meta;
type Story = StoryObj<typeof MapDetailCard>;

export const Default: Story = {
  play: async ({ canvasElement }) => {
    const body = within(canvasElement.ownerDocument.body);
    const dialog = await body.findByRole('dialog', { name: 'Rose Cottage' });
    await expect(dialog).toBeVisible();
  },
};
