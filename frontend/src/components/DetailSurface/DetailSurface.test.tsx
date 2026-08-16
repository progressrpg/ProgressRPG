import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import DetailSurface from './DetailSurface';

function renderSurface(overrides: Partial<React.ComponentProps<typeof DetailSurface>> = {}) {
  const props = {
    open: true,
    title: 'Alice',
    onOpenChange: vi.fn(),
    children: <p>Card content</p>,
    ...overrides,
  };
  render(<DetailSurface {...props} />);
  return props;
}

describe('DetailSurface', () => {
  it('renders its children when open', () => {
    renderSurface();
    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByText('Card content')).toBeInTheDocument();
  });

  it('does not render when closed', () => {
    renderSurface({ open: false });
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('gives the dialog an accessible name from title', () => {
    renderSurface({ title: 'Rose Cottage' });
    expect(screen.getByRole('dialog', { name: 'Rose Cottage' })).toBeInTheDocument();
  });

  it('calls onOpenChange(false) when Escape is pressed', async () => {
    const user = userEvent.setup();
    const { onOpenChange } = renderSurface();
    await user.keyboard('{Escape}');
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });
});
