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

interface NavbarContextOptions {
  authenticated?: boolean;
  path?: string;
  featureFlags?: Record<string, unknown>;
  announcements?: AnnouncementListResponse;
}

/**
 * `Navbar` reads `useAuth()` (nav links), `useGame()` (unread-announcement
 * badge) and two `useFeatureFlag()` checks (`map`, `announcements`) that
 * resolve via a seeded `["appConfig"]` query - see `useFeatureFlag.ts`. Each
 * story seeds its own `QueryClient` and wraps in `MemoryRouter` since
 * `Navbar` reads the current route to highlight the active link.
 *
 * Since the initial route varies per story, this provider tree - including
 * `MemoryRouter` - is mounted once from `meta.decorators`, reading its
 * options from `context.parameters.navbarContext` rather than being
 * re-applied (and thus re-nesting `MemoryRouter`) via a per-story decorator.
 * Storybook composes story-level decorators with meta-level ones rather than
 * replacing them, so a per-story `MemoryRouter` here would double-nest it.
 */
function NavbarProviders({
  authenticated = true,
  path = '/timer',
  featureFlags = {},
  announcements,
  children,
}: NavbarContextOptions & { children: React.ReactNode }) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  queryClient.setQueryData(['appConfig'], { feature_flags: featureFlags });
  if (announcements) {
    queryClient.setQueryData(['announcements'], announcements);
  }

  return (
    <MemoryRouter initialEntries={[path]}>
      <QueryClientProvider client={queryClient}>
        <AuthContext.Provider value={mockAuthContextValue({ authenticated })}>
          <GameContext.Provider value={mockGameContextValue}>{children}</GameContext.Provider>
        </AuthContext.Provider>
      </QueryClientProvider>
    </MemoryRouter>
  );
}

const meta: Meta<typeof Navbar> = {
  title: 'Layout/Navbar',
  component: Navbar,
  tags: ['autodocs'],
  decorators: [
    (Story, context) => (
      <NavbarProviders {...(context.parameters.navbarContext as NavbarContextOptions | undefined)}>
        <Story />
      </NavbarProviders>
    ),
  ],
};

export default meta;
type Story = StoryObj<typeof Navbar>;

export const LoggedOut: Story = {
  parameters: { navbarContext: { authenticated: false, path: '/' } },
};

export const LoggedIn: Story = {};

/** `map` and `announcements` are `["testers"]`-gated by default - enabling them here via the seeded `appConfig` mirrors a tester/premium account. */
export const WithAnnouncements: Story = {
  parameters: {
    navbarContext: {
      featureFlags: { announcements: 'all' },
      announcements: {
        unread_count: 1,
        results: [
          {
            id: 1,
            title: 'New feature: the map is live',
            summary: 'Explore other characters at work on the world map.',
            body: 'The **map view** is now available from the nav bar. Highlights:\n\n- See other characters at work\n- Explore villages and buildings\n- [Read the announcement](https://example.com) for details',
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
    },
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.click(canvas.getByRole('button', { name: 'Announcements' }));

    // The announcements panel renders via a Radix Portal into document.body,
    // outside canvasElement, so it must be queried from the document root.
    const body = within(canvasElement.ownerDocument.body);
    await waitFor(async () => {
      await expect(body.getByText('New feature: the map is live')).toBeVisible();
    });
  },
};

export const WithMapEnabled: Story = {
  parameters: { navbarContext: { featureFlags: { map: 'all' } } },
};
