import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { TamaguiProvider } from 'tamagui';
import DetailCard from './DetailCard';
import tamaguiConfig from '../../../tamagui.config';

// DetailCard's underlying DetailSurface (#799) needs a TamaguiProvider
// ancestor - the app root (src/main.tsx) provides this in production;
// tests need their own.
function renderCard(overrides: Partial<React.ComponentProps<typeof DetailCard>> = {}) {
  const props = {
    open: true,
    title: 'Alice',
    onClose: vi.fn(),
    children: <p>Card content</p>,
    ...overrides,
  };
  render(
    <TamaguiProvider config={tamaguiConfig} defaultTheme="light">
      <DetailCard {...props} />
    </TamaguiProvider>
  );
  return props;
}

describe('DetailCard', () => {
  it('renders the title and content when open', () => {
    renderCard();
    expect(screen.getByRole('dialog', { name: 'Alice' })).toBeInTheDocument();
    expect(screen.getAllByText('Alice').length).toBeGreaterThan(0);
    expect(screen.getByText('Card content')).toBeInTheDocument();
  });

  it('does not render when closed', () => {
    renderCard({ open: false });
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('calls onClose when the close button is clicked', async () => {
    const user = userEvent.setup();
    const { onClose } = renderCard();
    await user.click(screen.getByRole('button', { name: 'Close' }));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('calls onClose when Escape is pressed', async () => {
    const user = userEvent.setup();
    const { onClose } = renderCard();
    await user.keyboard('{Escape}');
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
