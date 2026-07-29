// PoC (issue #629): the existing Tooltip.test.tsx suite (3 cases), run
// unmodified in intent against the Tamagui swap, per the spike's acceptance
// criteria ("run the existing Tooltip test suite... report pass/fail per
// case"). Import swapped to the Tamagui version; assertions are identical.
import { describe, it, expect } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { TamaguiProvider } from 'tamagui';

import TooltipTamagui, { TooltipProviderTamagui } from './Tooltip.tamagui';
import tamaguiConfig from '../../../tamagui.config';

function renderTooltip() {
  render(
    <TamaguiProvider config={tamaguiConfig}>
      <TooltipProviderTamagui delayDuration={0} skipDelayDuration={0}>
        <TooltipTamagui content="Helpful context">
          <button type="button">Hover me</button>
        </TooltipTamagui>
      </TooltipProviderTamagui>
    </TamaguiProvider>
  );
}

describe('Tooltip (Tamagui PoC)', () => {
  it('shows on hover and hides when the pointer leaves', async () => {
    const user = userEvent.setup();

    renderTooltip();

    await user.hover(screen.getByRole('button', { name: 'Hover me' }));
    expect(await screen.findByRole('tooltip')).toHaveTextContent('Helpful context');

    await user.unhover(screen.getByRole('button', { name: 'Hover me' }));

    await waitFor(() => {
      expect(screen.queryByRole('tooltip')).not.toBeInTheDocument();
    });
  });

  // PoC finding: FAILS, and it's a real, verified gap - not a config miss.
  // Radix opens tooltips on focus with no opt-in. Tamagui's Tooltip exposes
  // a `focus={{ enabled: true }}` prop for this (see Tooltip.tamagui.tsx),
  // which was tried here; the tooltip still never opens on `user.tab()` in
  // this RTL/happy-dom environment (confirmed via a controlled `open=true`
  // diagnostic that the Content/aria-describedby wiring itself is correct -
  // see .claude/plans/issue-629-tamagui-poc.md - so this is specifically the
  // focus-trigger path not firing, not a broader rendering failure).
  it.fails('shows on focus and wires the trigger to aria-describedby', async () => {
    const user = userEvent.setup();

    renderTooltip();

    await user.tab();

    const trigger = screen.getByRole('button', { name: 'Hover me' });
    const tooltip = await screen.findByRole('tooltip');

    expect(trigger).toHaveFocus();
    expect(trigger).toHaveAttribute('aria-describedby', tooltip.id);
  });

  // PoC finding: FAILS, same root cause as above - this suite's only way to
  // open the tooltip for an Escape-dismiss check is via focus (`user.tab()`),
  // which doesn't open it here.
  it.fails('dismisses when Escape is pressed', async () => {
    const user = userEvent.setup();

    renderTooltip();

    await user.tab();
    expect(await screen.findByRole('tooltip')).toBeInTheDocument();

    await user.keyboard('{Escape}');

    await waitFor(() => {
      expect(screen.queryByRole('tooltip')).not.toBeInTheDocument();
    });
  });
});
