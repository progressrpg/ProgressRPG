import type { Meta, StoryObj } from '@storybook/react-vite';
import { MemoryRouter } from 'react-router';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { expect, userEvent, waitFor, within } from 'storybook/test';
import Navbar from './Navbar';
import { AuthContext } from '../../context/authContext';
import { GameContext } from '../../context/gameContext';
import { mockAuthContextValue } from '../../testUtils/mockAuthContext';
import { mockGameContextValue } from '../../testUtils/mockGameContext';
import type { AnnouncementListResponse } from '../../types';

/**
 * `Navbar` reads `useAuth()` (nav links), `useGame()` (unread-announcement
 * badge) and two `useFeatureFlag()` checks (`map`, `announcements`) that
 * resolve via a seeded `["appConfig"]` query - see `useFeatureFlag.ts`. Each
 * story seeds its own `QueryClient` and wraps in `MemoryRouter` since
 * `Navbar` reads the current route to highlight the active link.
 */
function withNavbarContext({
  authenticated = true,
  path = '/timer',
  featureFlags = {},
  announcements,
}: {
  authenticated?: boolean;
  path?: string;
  featureFlags?: Record<string, unknown>;
  announcements?: AnnouncementListResponse;
}) {
  return (Story: () => React.ReactElement) => {
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    queryClient.setQueryData(['appConfig'], { feature_flags: featureFlags });
    if (announcements) {
      queryClient.setQueryData(['announcements'], announcements);
    }

    return (
      <MemoryRouter initialEntries={[path]}>
        <QueryClientProvider client={queryClient}>
          <AuthContext.Provider value={mockAuthContextValue({ authenticated })}>
            <GameContext.Provider value={mockGameContextValue}>
              <Story />
            </GameContext.Provider>
          </AuthContext.Provider>
        </QueryClientProvider>
      </MemoryRouter>
    );
  };
}

const meta: Meta<typeof Navbar> = {
  title: 'Layout/Navbar',
  component: Navbar,
  tags: ['autodocs'],
  decorators: [withNavbarContext({})],
};

export default meta;
type Story = StoryObj<typeof Navbar>;

export const LoggedOut: Story = {
  decorators: [withNavbarContext({ authenticated: false, path: '/' })],
};

export const LoggedIn: Story = {};

/** `map` and `announcements` are `["testers"]`-gated by default - enabling them here via the seeded `appConfig` mirrors a tester/premium account. */
export const WithAnnouncements: Story = {
  decorators: [
    withNavbarContext({
      featureFlags: { announcements: 'all' },
      announcements: {
        unread_count: 1,
        results: [
          {
            id: 1,
            title: 'New feature: the map is live',
            summary: 'Explore other characters at work on the world map.',
            body: 'The map view is now available from the nav bar.',
            published_at: '2026-08-01T00:00:00Z',
            created_at: '2026-08-01T00:00:00Z',
            is_read: false,
          },
          {
            id: 2,
            title: 'Scheduled maintenance',
            summary: 'Brief downtime overnight on Aug 20.',
            body: 'We are upgrading database infrastructure.',
            published_at: '2026-07-20T00:00:00Z',
            created_at: '2026-07-20T00:00:00Z',
            is_read: true,
          },
        ],
      },
    }),
  ],
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.click(canvas.getByRole('button', { name: 'Announcements' }));

    await waitFor(async () => {
      await expect(canvas.getByText('New feature: the map is live')).toBeVisible();
    });
  },
};

export const WithMapEnabled: Story = {
  decorators: [withNavbarContext({ featureFlags: { map: 'all' } })],
};
