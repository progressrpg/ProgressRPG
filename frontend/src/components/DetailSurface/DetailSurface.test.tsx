import { useState } from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { TamaguiProvider } from 'tamagui';
import DetailSurface from './DetailSurface';
import tamaguiConfig from '../../../tamagui.config';

// Tamagui's Dialog (#799) needs a TamaguiProvider ancestor - unlike Radix's
// Dialog.Root, it isn't usable standalone. The app root (src/main.tsx)
// provides this in production; tests need their own.
function renderWithProvider(ui: React.ReactElement) {
  return render(
    <TamaguiProvider config={tamaguiConfig} defaultTheme="light">
      {ui}
    </TamaguiProvider>
  );
}

function renderSurface(overrides: Partial<React.ComponentProps<typeof DetailSurface>> = {}) {
  const props = {
    open: true,
    title: 'Alice',
    onOpenChange: vi.fn(),
    children: <p>Card content</p>,
    ...overrides,
  };
  renderWithProvider(<DetailSurface {...props} />);
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

  it('restores focus to the previously focused element on close', async () => {
    const user = userEvent.setup();

    function Harness() {
      const [open, setOpen] = useState(false);
      return (
        <>
          <button onClick={() => setOpen(true)}>Open</button>
          <DetailSurface
            open={open}
            onOpenChange={setOpen}
            title="Alice"
          >
            <button onClick={() => setOpen(false)}>Close</button>
          </DetailSurface>
        </>
      );
    }

    renderWithProvider(<Harness />);

    const openButton = screen.getByRole('button', { name: 'Open' });
    openButton.focus();
    await user.click(openButton);

    await user.click(await screen.findByRole('button', { name: 'Close' }));

    await waitFor(() => expect(openButton).toHaveFocus());
  });

  describe('container', () => {
    it('renders Dialog.Content as a descendant of the given container', async () => {
      const container = document.createElement('div');
      document.body.appendChild(container);

      renderSurface({ container });

      await waitFor(() => {
        expect(container.querySelector('[role="dialog"]')).not.toBeNull();
      });

      document.body.removeChild(container);
    });

    it('does not render into the container when closed', () => {
      const container = document.createElement('div');
      document.body.appendChild(container);

      renderSurface({ container, open: false });

      expect(container.querySelector('[role="dialog"]')).toBeNull();

      document.body.removeChild(container);
    });

    it('falls back to the default portal when container is null', () => {
      renderSurface({ container: null });
      expect(screen.getByRole('dialog')).toBeInTheDocument();
    });
  });

  describe('modal={false}', () => {
    it('renders no overlay and does not dismiss on outside click', async () => {
      const user = userEvent.setup();
      const container = document.createElement('div');
      document.body.appendChild(container);

      const { onOpenChange } = renderSurface({ modal: false, container });
      await screen.findByRole('dialog');

      await user.click(document.body);

      expect(onOpenChange).not.toHaveBeenCalledWith(false);
      expect(screen.getByRole('dialog')).toBeInTheDocument();

      document.body.removeChild(container);
    });
  });
});
