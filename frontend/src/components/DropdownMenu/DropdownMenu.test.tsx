import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { TamaguiProvider } from 'tamagui';
import DropdownMenu from './DropdownMenu';
import tamaguiConfig from '../../../tamagui.config';

// Tamagui's Menu (#586) needs a TamaguiProvider ancestor - unlike Radix's
// DropdownMenu.Root, it isn't usable standalone. The app root (src/main.tsx)
// provides this in production; tests need their own.
function renderWithProvider(ui: React.ReactElement) {
  return render(
    <TamaguiProvider config={tamaguiConfig} defaultTheme="light">
      {ui}
    </TamaguiProvider>
  );
}

function renderMenu({
  onAccountSelect,
  onToggleSelect,
}: { onAccountSelect?: () => void; onToggleSelect?: () => void } = {}) {
  renderWithProvider(
    <>
      <DropdownMenu.Root>
        <DropdownMenu.Trigger>Account menu</DropdownMenu.Trigger>
        <DropdownMenu.Portal>
          <DropdownMenu.Content>
            <DropdownMenu.Item onSelect={onToggleSelect}>Tutorial</DropdownMenu.Item>
            <DropdownMenu.Item asChild onSelect={onAccountSelect}>
              <a href="/account">Account</a>
            </DropdownMenu.Item>
          </DropdownMenu.Content>
        </DropdownMenu.Portal>
      </DropdownMenu.Root>
      <button type="button">Elsewhere</button>
    </>
  );
}

describe('DropdownMenu', () => {
  it('is closed by default and opens when the trigger is clicked', async () => {
    const user = userEvent.setup();
    renderMenu();

    expect(screen.queryByRole('menu')).not.toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Account menu' }));
    expect(await screen.findByRole('menu')).toBeInTheDocument();
    expect(screen.getByRole('menuitem', { name: 'Tutorial' })).toBeInTheDocument();
    expect(screen.getByRole('menuitem', { name: 'Account' })).toBeInTheDocument();
  });

  it('exposes aria-haspopup/aria-expanded/aria-controls on the trigger', async () => {
    const user = userEvent.setup();
    renderMenu();

    const trigger = screen.getByRole('button', { name: 'Account menu' });
    expect(trigger).toHaveAttribute('aria-haspopup', 'menu');
    expect(trigger).toHaveAttribute('aria-expanded', 'false');

    await user.click(trigger);
    const menu = await screen.findByRole('menu');

    expect(trigger).toHaveAttribute('aria-expanded', 'true');
    expect(trigger).toHaveAttribute('aria-controls', menu.id);
  });

  it('navigates between items with arrow keys', async () => {
    const user = userEvent.setup();
    renderMenu();

    await user.click(screen.getByRole('button', { name: 'Account menu' }));
    await screen.findByRole('menu');

    await user.keyboard('{ArrowDown}');
    expect(screen.getByRole('menuitem', { name: 'Tutorial' })).toHaveFocus();

    await user.keyboard('{ArrowDown}');
    expect(screen.getByRole('menuitem', { name: 'Account' })).toHaveFocus();
  });

  it('closes on outside click and Escape', async () => {
    // Tamagui's Menu is modal by default (matching Radix's DropdownMenu.Root
    // default) and disables pointer events on the rest of the page while
    // open - real browser behaviour, not a test artefact (AlertDialog's
    // #582 test hit the same thing) - so skip userEvent's pointer-events
    // guard to let the click still dispatch.
    const user = userEvent.setup({ pointerEventsCheck: 0 });
    renderMenu();

    await user.click(screen.getByRole('button', { name: 'Account menu' }));
    await screen.findByRole('menu');
    await user.click(screen.getByRole('button', { name: 'Elsewhere' }));
    await waitFor(() => expect(screen.queryByRole('menu')).not.toBeInTheDocument());

    await user.click(screen.getByRole('button', { name: 'Account menu' }));
    await screen.findByRole('menu');
    await user.keyboard('{Escape}');
    await waitFor(() => expect(screen.queryByRole('menu')).not.toBeInTheDocument());
  });

  it('returns focus to the trigger after Escape closes the menu', async () => {
    const user = userEvent.setup();
    renderMenu();

    const trigger = screen.getByRole('button', { name: 'Account menu' });
    await user.click(trigger);
    await screen.findByRole('menu');
    await user.keyboard('{Escape}');

    await waitFor(() => expect(trigger).toHaveFocus());
  });

  it('a plain item fires onSelect and closes the menu on click', async () => {
    const user = userEvent.setup();
    const onToggleSelect = vi.fn();
    renderMenu({ onToggleSelect });

    await user.click(screen.getByRole('button', { name: 'Account menu' }));
    await user.click(screen.getByRole('menuitem', { name: 'Tutorial' }));

    expect(onToggleSelect).toHaveBeenCalledTimes(1);
    await waitFor(() => expect(screen.queryByRole('menu')).not.toBeInTheDocument());
  });

  it('an asChild link item navigates, fires onSelect, and closes the menu', async () => {
    const user = userEvent.setup();
    const onAccountSelect = vi.fn();
    renderMenu({ onAccountSelect });

    await user.click(screen.getByRole('button', { name: 'Account menu' }));
    const link = screen.getByRole('menuitem', { name: 'Account' });
    expect(link.tagName).toBe('A');
    expect(link).toHaveAttribute('href', '/account');

    await user.click(link);

    expect(onAccountSelect).toHaveBeenCalledTimes(1);
    await waitFor(() => expect(screen.queryByRole('menu')).not.toBeInTheDocument());
  });

  it('an asChild link item also closes the menu via keyboard activation', async () => {
    const user = userEvent.setup();
    renderMenu();

    await user.click(screen.getByRole('button', { name: 'Account menu' }));
    await user.keyboard('{ArrowDown}{ArrowDown}');
    expect(screen.getByRole('menuitem', { name: 'Account' })).toHaveFocus();

    await user.keyboard('{Enter}');
    await waitFor(() => expect(screen.queryByRole('menu')).not.toBeInTheDocument());
  });
});
