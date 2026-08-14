import type { Meta, StoryObj } from '@storybook/react-vite';
import StaticBanner from './StaticBanner';

/**
 * `StaticBanner` is a single-line site announcement. It renders nothing
 * when `message` is empty/unset, so a running app with no announcement
 * configured shows no banner at all.
 */
const meta: Meta<typeof StaticBanner> = {
  title: 'Shared/StaticBanner',
  component: StaticBanner,
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj<typeof StaticBanner>;

export const Default: Story = {
  args: { message: "Scheduled maintenance tonight at 10pm UTC - the app may be briefly unavailable." },
};

/** No `message` - renders nothing. */
export const NoMessage: Story = {
  args: {},
};
