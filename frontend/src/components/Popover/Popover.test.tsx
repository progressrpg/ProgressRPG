import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { TamaguiProvider } from 'tamagui';
import Popover from './Popover';
import tamaguiConfig from '../../../tamagui.config';

// Tamagui's Popover (#585) needs a TamaguiProvider ancestor - unlike Radix's
// Popover.Root, it isn't usable standalone. The app root (src/main.tsx)
// provides this in production; tests need their own.
function renderWithProvider(ui: React.ReactElement) {
  return render(
    <TamaguiProvider config={tamaguiConfig} defaultTheme="light">
      {ui}
    </TamaguiProvider>
  );
}

function renderPopover(props: Partial<React.ComponentProps<typeof Popover.Root>> = {}) {
  renderWithProvider(
    <>
      <Popover.Root {...props}>
        <Popover.Trigger asChild>
          <button type="button">Trigger</button>
        </Popover.Trigger>
        <Popover.Content>
          <Popover.Close asChild>
            <button type="button">Close</button>
          </Popover.Close>
          <p>Panel content</p>
        </Popover.Content>
      </Popover.Root>
      <button type="button">Elsewhere</button>
    </>
  );
}

describe('Popover', () => {
  it('is closed by default and opens when the trigger is clicked', async () => {
    const user = userEvent.setup();
    renderPopover();

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Trigger' }));
    expect(await screen.findByRole('dialog')).toHaveTextContent('Panel content');
  });

  it('toggles closed when the trigger is clicked again', async () => {
    const user = userEvent.setup();
    renderPopover();

    const trigger = screen.getByRole('button', { name: 'Trigger' });
    await user.click(trigger);
    await screen.findByRole('dialog');

    await user.click(trigger);
    await waitFor(() => {
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    });
  });

  it('closes via the Close button and returns focus to the trigger', async () => {
    const user = userEvent.setup();
    renderPopover();

    const trigger = screen.getByRole('button', { name: 'Trigger' });
    await user.click(trigger);
    await user.click(await screen.findByRole('button', { name: 'Close' }));

    await waitFor(() => {
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    });
    expect(trigger).toHaveFocus();
  });

  it('closes on outside click', async () => {
    const user = userEvent.setup();
    renderPopover();

    await user.click(screen.getByRole('button', { name: 'Trigger' }));
    await screen.findByRole('dialog');

    await user.click(screen.getByRole('button', { name: 'Elsewhere' }));

    await waitFor(() => {
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    });
  });

  it('closes on Escape', async () => {
    const user = userEvent.setup();
    renderPopover();

    await user.click(screen.getByRole('button', { name: 'Trigger' }));
    await screen.findByRole('dialog');

    await user.keyboard('{Escape}');

    await waitFor(() => {
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    });
  });

  it('exposes aria-expanded and aria-controls on the trigger', async () => {
    const user = userEvent.setup();
    renderPopover();

    const trigger = screen.getByRole('button', { name: 'Trigger' });
    expect(trigger).toHaveAttribute('aria-expanded', 'false');
    expect(trigger).not.toHaveAttribute('aria-controls');

    await user.click(trigger);
    await screen.findByRole('dialog');

    expect(trigger).toHaveAttribute('aria-expanded', 'true');
    const controlsId = trigger.getAttribute('aria-controls');
    expect(controlsId).toBeTruthy();
    expect(document.getElementById(controlsId!)).toHaveTextContent('Panel content');
  });

  it('supports a controlled open state', async () => {
    const onOpenChange = vi.fn();
    renderPopover({ open: true, onOpenChange });

    expect(await screen.findByRole('dialog')).toBeInTheDocument();
  });
});
