import type { Meta, StoryObj } from '@storybook/react-vite';
import { MemoryRouter } from 'react-router';
import { expect, within } from 'storybook/test';
import Footer from './Footer';
import { AuthContext } from '../../context/authContext';
import { mockAuthContextValue } from '../../testUtils/mockAuthContext';

/**
 * `Footer` reads `useAuth()` only, to gate the "Admin Panel" link behind a
 * staff user. Wrapped in `MemoryRouter` since its internal links use
 * `react-router`'s `Link`.
 */
function withAuth(overrides: Parameters<typeof mockAuthContextValue>[0] = {}) {
  return (Story: () => React.ReactElement) => (
    <MemoryRouter>
      <AuthContext.Provider value={mockAuthContextValue(overrides)}>
        <Story />
      </AuthContext.Provider>
    </MemoryRouter>
  );
}

const meta: Meta<typeof Footer> = {
  title: 'Layout/Footer',
  component: Footer,
  tags: ['autodocs'],
  decorators: [withAuth()],
};

export default meta;
type Story = StoryObj<typeof Footer>;

export const LoggedOut: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(canvas.getByRole('link', { name: 'Support' })).toBeVisible();
    await expect(canvas.queryByRole('link', { name: 'Admin Panel' })).not.toBeInTheDocument();
  },
};

export const LoggedIn: Story = {
  decorators: [withAuth({ authenticated: true })],
};

export const StaffUser: Story = {
  decorators: [
    withAuth({
      authenticated: true,
      user: { email: 'staff@example.com', is_confirmed: true, is_staff: true, is_superuser: false, date_of_birth: null, timezone: 'UTC' },
    }),
  ],
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(canvas.getByRole('link', { name: 'Admin Panel' })).toBeVisible();
  },
};
