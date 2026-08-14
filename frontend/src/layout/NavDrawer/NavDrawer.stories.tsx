import type { Meta, StoryObj } from '@storybook/react-vite';
import { MemoryRouter } from 'react-router';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { expect, fn, userEvent, within } from 'storybook/test';
import NavDrawer from './NavDrawer';
import { AuthContext } from '../../context/authContext';
import { GameContext } from '../../context/gameContext';
import { mockAuthContextValue } from '../../testUtils/mockAuthContext';
import { mockGameContextValue } from '../../testUtils/mockGameContext';

/**
 * `NavDrawer` is the mobile side-nav - it reads `useAuth()` for which links
 * to show and `useFeatureFlag("map")` (via a seeded `["appConfig"]` query,
 * see `useFeatureFlag.ts`) to gate the Map link. Rendered inline via
 * `parameters.docs.story` since it's a fixed-position overlay, not
 * document-flow content.
 */
function withNavDrawerContext({
  authenticated = true,
  featureFlags = {},
}: {
  authenticated?: boolean;
  featureFlags?: Record<string, unknown>;
}) {
  return (Story: () => React.ReactElement) => {
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    queryClient.setQueryData(['appConfig'], { feature_flags: featureFlags });

    return (
      <MemoryRouter>
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

const meta: Meta<typeof NavDrawer> = {
  title: 'Layout/NavDrawer',
  component: NavDrawer,
  tags: ['autodocs'],
  parameters: {
    docs: {
      story: { inline: true, iframeHeight: 360 },
    },
  },
  args: {
    drawerOpen: true,
    onClose: fn(),
  },
  decorators: [withNavDrawerContext({})],
};

export default meta;
type Story = StoryObj<typeof NavDrawer>;

export const LoggedIn: Story = {
  play: async ({ canvasElement, args }) => {
    const canvas = within(canvasElement);
    await expect(canvas.getByRole('link', { name: /Timer/ })).toBeVisible();

    await userEvent.click(canvas.getByRole('button', { name: 'Close navigation drawer' }));
    await expect(args.onClose).toHaveBeenCalled();
  },
};

export const LoggedOut: Story = {
  decorators: [withNavDrawerContext({ authenticated: false })],
};

/** `map` is `["testers"]`-gated by default - enabling it here mirrors a tester/premium account. */
export const WithMapEnabled: Story = {
  decorators: [withNavDrawerContext({ featureFlags: { map: 'all' } })],
};

export const Closed: Story = {
  args: { drawerOpen: false },
};
