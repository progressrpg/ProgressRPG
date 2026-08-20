import { describe, it, expect } from 'vitest';
import { render as rtlRender, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { TamaguiProvider } from 'tamagui';
import Tooltip, { TooltipProvider } from './Tooltip';
import tamaguiConfig from '../../../tamagui.config';

// Tamagui's Tooltip (#583) needs a TamaguiProvider ancestor - unlike Radix's
// Tooltip.Root, it isn't usable standalone. The app root (src/main.tsx)
// provides this in production; tests need their own.
function render(...args: Parameters<typeof rtlRender>) {
  const [ui, options] = args;
  return rtlRender(ui, {
    wrapper: ({ children }) => (
      <TamaguiProvider config={tamaguiConfig} defaultTheme="light">
        {children}
      </TamaguiProvider>
    ),
    ...options,
  });
}

function renderTooltip() {
  render(
    <TooltipProvider delayDuration={0} skipDelayDuration={0}>
      <Tooltip content="Helpful context">
        <button type="button">Trigger</button>
      </Tooltip>
      <button type="button">Elsewhere</button>
    </TooltipProvider>
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
    expect(trigger).toHaveAttribute('aria-describedby', tooltip.id);
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

  it('renders only the trigger, with no tooltip behaviour, when disabled', async () => {
    const user = userEvent.setup();

    render(
      <Tooltip content="Helpful context" disabled>
        <button type="button">Trigger</button>
      </Tooltip>
    );

    const trigger = screen.getByRole('button', { name: 'Trigger' });
    await user.click(trigger);

    expect(screen.queryByRole('tooltip')).not.toBeInTheDocument();
  });

  it.each([null, undefined, false])(
    'renders only the trigger when content is %s',
    async (content) => {
      const user = userEvent.setup();

      render(
        <Tooltip content={content}>
          <button type="button">Trigger</button>
        </Tooltip>
      );

      const trigger = screen.getByRole('button', { name: 'Trigger' });
      await user.click(trigger);

      expect(screen.queryByRole('tooltip')).not.toBeInTheDocument();
    }
  );

  it('TooltipProvider renders its children as a passthrough', () => {
    render(
      <TooltipProvider>
        <span>Provider child</span>
      </TooltipProvider>
    );

    expect(screen.getByText('Provider child')).toBeInTheDocument();
  });
});
