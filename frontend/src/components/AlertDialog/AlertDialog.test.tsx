import { useState } from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { TamaguiProvider } from 'tamagui';
import AlertDialog from './AlertDialog';
import tamaguiConfig from '../../../tamagui.config';

// AlertDialog's underlying Tamagui `AlertDialog` (#582) needs a
// TamaguiProvider ancestor - unlike Radix's AlertDialog.Root, it isn't
// usable standalone. The app root (src/main.tsx) provides this in
// production; tests need their own.
function renderWithProvider(ui: React.ReactElement) {
  return render(
    <TamaguiProvider config={tamaguiConfig} defaultTheme="light">
      {ui}
    </TamaguiProvider>
  );
}

function renderDialog(overrides: Partial<React.ComponentProps<typeof AlertDialog>> = {}) {
  const props = {
    open: true,
    title: 'Confirm action',
    description: 'Are you sure you want to proceed?',
    onConfirm: vi.fn(),
    onCancel: vi.fn(),
    ...overrides,
  };
  renderWithProvider(<AlertDialog {...props} />);
  return props;
}

describe('AlertDialog', () => {
  it('renders title and description when open', () => {
    renderDialog();
    expect(screen.getByRole('alertdialog')).toBeInTheDocument();
    expect(screen.getByText('Confirm action')).toBeInTheDocument();
    expect(screen.getByText('Are you sure you want to proceed?')).toBeInTheDocument();
  });

  it('does not render when closed', () => {
    renderDialog({ open: false });
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
  });

  it('calls onConfirm when the confirm button is clicked', async () => {
    const user = userEvent.setup();
    const { onConfirm } = renderDialog({ confirmLabel: 'Yes, do it' });
    await user.click(screen.getByRole('button', { name: 'Yes, do it' }));
    expect(onConfirm).toHaveBeenCalledTimes(1);
  });

  it('calls onCancel when the cancel button is clicked', async () => {
    const user = userEvent.setup();
    const { onCancel } = renderDialog({ cancelLabel: 'No thanks' });
    await user.click(screen.getByRole('button', { name: 'No thanks' }));
    expect(onCancel).toHaveBeenCalledTimes(1);
  });

  it('calls onCancel when Escape is pressed', async () => {
    const user = userEvent.setup();
    const { onCancel } = renderDialog();
    await user.keyboard('{Escape}');
    expect(onCancel).toHaveBeenCalledTimes(1);
  });

  it('wires aria-describedby to the description', () => {
    renderDialog();
    const dialog = screen.getByRole('alertdialog');
    const descId = dialog.getAttribute('aria-describedby');
    expect(descId).toBeTruthy();
    expect(document.getElementById(descId!)).toHaveTextContent('Are you sure you want to proceed?');
  });

  it('focuses the Cancel button when opened, not the confirm action', async () => {
    renderDialog({ confirmLabel: 'Delete', variant: 'destructive' });
    await vi.waitFor(() => {
      expect(screen.getByRole('button', { name: 'Cancel' })).toHaveFocus();
    });
  });

  it('does not close when clicking outside the dialog', async () => {
    // The modal dismissable layer disables pointer events on the rest of
    // the page while open (real browser behaviour, not a test artefact) -
    // skip userEvent's pointer-events guard so the click still dispatches,
    // to assert it's a no-op rather than that it's unreachable.
    const user = userEvent.setup({ pointerEventsCheck: 0 });
    const onCancel = vi.fn();

    function Harness() {
      return (
        <>
          <button>Outside</button>
          <AlertDialog
            open
            title="Confirm action"
            description="Are you sure you want to proceed?"
            onConfirm={() => {}}
            onCancel={onCancel}
          />
        </>
      );
    }

    renderWithProvider(<Harness />);
    await user.click(screen.getByRole('button', { name: 'Outside' }));

    expect(onCancel).not.toHaveBeenCalled();
    expect(screen.getByRole('alertdialog')).toBeInTheDocument();
  });

  it('restores focus to the previously focused element on close', async () => {
    const user = userEvent.setup();

    function Harness() {
      const [open, setOpen] = useState(false);
      return (
        <>
          <button onClick={() => setOpen(true)}>Open</button>
          <AlertDialog
            open={open}
            title="Confirm action"
            description="Are you sure you want to proceed?"
            onConfirm={() => setOpen(false)}
            onCancel={() => setOpen(false)}
          />
        </>
      );
    }

    renderWithProvider(<Harness />);

    const openButton = screen.getByRole('button', { name: 'Open' });
    openButton.focus();
    await user.click(openButton);

    const cancelButton = await screen.findByRole('button', { name: 'Cancel' });
    await user.click(cancelButton);

    expect(openButton).toHaveFocus();
  });
});
