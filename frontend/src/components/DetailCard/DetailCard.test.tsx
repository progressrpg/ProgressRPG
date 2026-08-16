import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import DetailCard from './DetailCard';

function renderCard(overrides: Partial<React.ComponentProps<typeof DetailCard>> = {}) {
  const props = {
    open: true,
    title: 'Alice',
    onClose: vi.fn(),
    children: <p>Card content</p>,
    ...overrides,
  };
  render(<DetailCard {...props} />);
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
