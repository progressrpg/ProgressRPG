import { describe, it, expect } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { TamaguiProvider } from 'tamagui';
import Tooltip, { TooltipProvider } from './Tooltip';
import tamaguiConfig from '../../../tamagui.config';

function renderTooltip() {
  render(
    <TamaguiProvider config={tamaguiConfig} defaultTheme="light">
      <TooltipProvider delayDuration={0} skipDelayDuration={0}>
        <Tooltip content="Helpful context">
          <button type="button">Trigger</button>
        </Tooltip>
        <button type="button">Elsewhere</button>
      </TooltipProvider>
    </TamaguiProvider>
  );
}

describe('Tooltip', () => {
  it('does not open on hover', async () => {
    const user = userEvent.setup();

    renderTooltip();

    await user.hover(screen.getByRole('button', { name: 'Trigger' }));

    expect(screen.queryByRole('tooltip')).not.toBeInTheDocument();
  });

  it('opens on click and closes when the trigger is clicked again', async () => {
    const user = userEvent.setup();

    renderTooltip();

    const trigger = screen.getByRole('button', { name: 'Trigger' });

    await user.click(trigger);
    expect(await screen.findByRole('tooltip')).toHaveTextContent('Helpful context');

    await user.click(trigger);
    await waitFor(() => {
      expect(screen.queryByRole('tooltip')).not.toBeInTheDocument();
    });
  });

  it('closes when clicking outside the trigger, including unrelated elements', async () => {
    const user = userEvent.setup();

    renderTooltip();

    await user.click(screen.getByRole('button', { name: 'Trigger' }));
    expect(await screen.findByRole('tooltip')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Elsewhere' }));

    await waitFor(() => {
      expect(screen.queryByRole('tooltip')).not.toBeInTheDocument();
    });
  });

  it('shows on focus and wires the trigger to aria-describedby', async () => {
    const user = userEvent.setup();

    renderTooltip();

    await user.tab();

    const trigger = screen.getByRole('button', { name: 'Trigger' });
    const tooltip = await screen.findByRole('tooltip');

    expect(trigger).toHaveFocus();

    // Radix's role="tooltip" element and its description-bearing id were
    // the same node. Tamagui's floating positioning wrapper (role="tooltip")
    // and the content frame this component sets its own explicit id on
    // (see Tooltip.tsx's contentId) are two different, nested elements -
    // confirmed by reading the rendered DOM, not assumed. aria-describedby
    // pointing at the inner content frame is still valid: the reference
    // only needs to resolve to an element carrying the descriptive text, not
    // specifically the role="tooltip" node itself, and this is what a
    // screen reader actually reads out.
    const describedById = trigger.getAttribute('aria-describedby');
    expect(describedById).toBeTruthy();
    const describedByEl = document.getElementById(describedById ?? '');
    expect(describedByEl).not.toBeNull();
    expect(tooltip.contains(describedByEl)).toBe(true);
    expect(describedByEl).toHaveTextContent('Helpful context');
  });

  it('dismisses when Escape is pressed', async () => {
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
