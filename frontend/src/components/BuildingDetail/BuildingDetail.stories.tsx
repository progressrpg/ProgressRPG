import type { Meta, StoryObj } from '@storybook/react-vite';
import { fn } from 'storybook/test';
import BuildingDetail from './BuildingDetail';
import DetailCard from '../DetailCard/DetailCard';

/**
 * `BuildingDetail` is the building-specific content shown inside
 * `DetailCard`. Unlike `CharacterDetail`, it takes plain props rather than
 * fetching its own data - residents/occupancy/goods are all already
 * available from the map's own feature data (see Map.tsx, which derives
 * these props from the building's own feature plus already-loaded
 * character features matching its `home_id`).
 */
const meta: Meta<typeof BuildingDetail> = {
  title: 'Map/BuildingDetail',
  component: BuildingDetail,
  tags: ['autodocs'],
  parameters: {
    docs: {
      story: { inline: false, iframeHeight: 400 },
    },
  },
  decorators: [
    (Story, { args }) => (
      <DetailCard open title={args.buildingType === 'residential' ? 'House' : 'Bakery'} onClose={fn()}>
        <Story />
      </DetailCard>
    ),
  ],
};

export default meta;
type Story = StoryObj<typeof BuildingDetail>;

export const House: Story = {
  args: {
    buildingType: 'residential',
    residentialCapacity: 6,
    residents: [
      { id: 1, name: 'Alice', currentActivity: 'idle' },
      { id: 2, name: 'Thomas', currentActivity: 'delivering goods to neighbours' },
      { id: 3, name: 'Emily', isMoving: true },
    ],
    onSelectResident: fn(),
  },
};

export const Workplace: Story = {
  args: {
    buildingType: 'bakery',
    residents: [],
    workerCount: 2,
    goods: [
      { good_type: 'flour', display: '3 sacks' },
      { good_type: 'bread', display: '18.0 loaves' },
    ],
  },
};

export const EmptyHouse: Story = {
  args: {
    buildingType: 'residential',
    residents: [],
    residentialCapacity: 4,
  },
};
