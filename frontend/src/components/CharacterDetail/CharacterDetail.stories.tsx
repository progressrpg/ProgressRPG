import type { Meta, StoryObj } from '@storybook/react-vite';
import { fn } from 'storybook/test';
import CharacterDetail from './CharacterDetail';
import DetailCard from '../DetailCard/DetailCard';

/**
 * `CharacterDetail` is the character-specific content shown inside
 * `DetailCard` on the map's second level of progressive disclosure
 * (tooltip -> click -> detail card). It fetches its own data
 * (`useMapCharacterDetail`) rather than receiving it as props, so this
 * story wraps it in `DetailCard` for a realistic preview but can't drive
 * real network data - see CharacterDetail.test.tsx for behaviour covered
 * against mocked fetch states.
 */
const meta: Meta<typeof CharacterDetail> = {
  title: 'Map/CharacterDetail',
  component: CharacterDetail,
  tags: ['autodocs'],
  parameters: {
    docs: {
      story: { inline: false, iframeHeight: 360 },
    },
  },
  decorators: [
    (Story) => (
      <DetailCard open title="Alice" onClose={fn()}>
        <Story />
      </DetailCard>
    ),
  ],
  args: {
    characterId: 1,
  },
};

export default meta;
type Story = StoryObj<typeof CharacterDetail>;

export const Default: Story = {};
