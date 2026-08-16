import { useState } from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { TamaguiProvider } from 'tamagui';
import Modal from './Modal';
import tamaguiConfig from '../../../tamagui.config';

// Modal's underlying Tamagui `Dialog` (#582) needs a TamaguiProvider
// ancestor - unlike Radix's Dialog.Root, it isn't usable standalone. The
// app root (src/main.tsx) provides this in production; tests need their own.
function renderModal(ui: React.ReactElement) {
  return render(
    <TamaguiProvider config={tamaguiConfig} defaultTheme="light">
      {ui}
    </TamaguiProvider>
  );
}

describe('Modal', () => {
  it('renders modal with title and children', () => {
    renderModal(
      <Modal title="Test Modal" onClose={() => {}}>
        <p>Modal content</p>
      </Modal>
    );

    expect(screen.getByText('Test Modal')).toBeInTheDocument();
    expect(screen.getByText('Modal content')).toBeInTheDocument();
  });

  it('renders close button with correct aria-label', () => {
    renderModal(
      <Modal title="Test Modal" onClose={() => {}}>
        <p>Content</p>
      </Modal>
    );

    const closeButton = screen.getByLabelText('Close modal');
    expect(closeButton).toBeInTheDocument();
  });

  it('calls onClose when close button is clicked', async () => {
    const user = userEvent.setup();
    const handleClose = vi.fn();

    renderModal(
      <Modal title="Test Modal" onClose={handleClose}>
        <p>Content</p>
      </Modal>
    );

    const closeButton = screen.getByLabelText('Close modal');
    await user.click(closeButton);

    expect(handleClose).toHaveBeenCalledTimes(1);
  });

  it('calls onClose when Escape key is pressed', async () => {
    const user = userEvent.setup();
    const handleClose = vi.fn();

    renderModal(
      <Modal title="Test Modal" onClose={handleClose}>
        <p>Content</p>
      </Modal>
    );

    await user.keyboard('{Escape}');

    expect(handleClose).toHaveBeenCalledTimes(1);
  });

  it('calls onClose when backdrop is clicked', async () => {
    const user = userEvent.setup();
    const handleClose = vi.fn();

    renderModal(
      <Modal title="Test Modal" onClose={handleClose}>
        <p>Content</p>
      </Modal>
    );

    const backdrop = screen.getByTestId('modal-overlay');
    await user.click(backdrop);

    expect(handleClose).toHaveBeenCalledTimes(1);
  });

  it('does not call onClose when modal content is clicked', async () => {
    const user = userEvent.setup();
    const handleClose = vi.fn();

    renderModal(
      <Modal title="Test Modal" onClose={handleClose}>
        <p>Content</p>
      </Modal>
    );

    const content = screen.getByText('Content');
    await user.click(content);

    expect(handleClose).not.toHaveBeenCalled();
  });

  it('works when onClose is not provided', async () => {
    const user = userEvent.setup();

    renderModal(
      <Modal title="Test Modal">
        <p>Content</p>
      </Modal>
    );

    const closeButton = screen.getByLabelText('Close modal');
    // Should not throw error
    await user.click(closeButton);
  });

  it('renders multiple children correctly', () => {
    renderModal(
      <Modal title="Test Modal" onClose={() => {}}>
        <p>First paragraph</p>
        <p>Second paragraph</p>
        <button>Action Button</button>
      </Modal>
    );

    expect(screen.getByText('First paragraph')).toBeInTheDocument();
    expect(screen.getByText('Second paragraph')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Action Button' })).toBeInTheDocument();
  });

  it('restores focus to the previously focused element on close', async () => {
    const user = userEvent.setup();

    function Harness() {
      const [open, setOpen] = useState(false);
      return (
        <>
          <button onClick={() => setOpen(true)}>Open</button>
          {open && (
            <Modal title="Test Modal" onClose={() => setOpen(false)}>
              <p>Content</p>
            </Modal>
          )}
        </>
      );
    }

    renderModal(<Harness />);

    const openButton = screen.getByRole('button', { name: 'Open' });
    openButton.focus();
    await user.click(openButton);

    const closeButton = await screen.findByLabelText('Close modal');
    await user.click(closeButton);

    expect(openButton).toHaveFocus();
  });
});
