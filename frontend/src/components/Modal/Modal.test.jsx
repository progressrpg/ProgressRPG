import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import Modal from './Modal';

describe('Modal', () => {
  it('renders modal with title and children', () => {
    render(
      <Modal title="Test Modal" onClose={() => {}}>
        <p>Modal content</p>
      </Modal>
    );
    
    expect(screen.getByText('Test Modal')).toBeInTheDocument();
    expect(screen.getByText('Modal content')).toBeInTheDocument();
  });

  it('renders close button with correct aria-label', () => {
    render(
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
    
    render(
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
    
    render(
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
    
    const { container } = render(
      <Modal title="Test Modal" onClose={handleClose}>
        <p>Content</p>
      </Modal>
    );
    
    const backdrop = container.firstChild;
    await user.click(backdrop);
    
    expect(handleClose).toHaveBeenCalledTimes(1);
  });

  it('does not call onClose when modal content is clicked', async () => {
    const user = userEvent.setup();
    const handleClose = vi.fn();
    
    render(
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
    
    render(
      <Modal title="Test Modal">
        <p>Content</p>
      </Modal>
    );
    
    const closeButton = screen.getByLabelText('Close modal');
    // Should not throw error
    await user.click(closeButton);
  });

  it('renders multiple children correctly', () => {
    render(
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
});
