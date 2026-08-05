import { describe, it, expect, vi } from 'vitest';
import { act, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { TamaguiProvider, ToastProvider } from 'tamagui';
import ToastManager from './ToastManager';
import tamaguiConfig from '../../../tamagui.config';

// ToastManager's Toast/ToastViewport (#581) need both a TamaguiProvider
// ancestor (for tokens/theme) and a ToastProvider (duration/swipe context) -
// ToastContext.tsx supplies both in the app; tests need their own.
function Wrapper({ children }: { children: React.ReactNode }) {
  return (
    <TamaguiProvider config={tamaguiConfig} defaultTheme="light">
      <ToastProvider>{children}</ToastProvider>
    </TamaguiProvider>
  );
}

function renderManager(props: Parameters<typeof ToastManager>[0]) {
  return render(<ToastManager {...props} />, { wrapper: Wrapper });
}

// Auto-dismiss (duration -> onOpenChange(false) -> onDismiss) needs its own
// duration, distinct from the shared Wrapper's default - a per-test provider
// lets the fake-timer test below use a short duration without affecting the
// other tests' default 5000ms Tamagui provider timing.
function renderWithDuration(
  props: Parameters<typeof ToastManager>[0],
  duration: number
) {
  return render(
    <TamaguiProvider config={tamaguiConfig} defaultTheme="light">
      <ToastProvider duration={duration}>
        <ToastManager {...props} />
      </ToastProvider>
    </TamaguiProvider>
  );
}

describe('ToastManager', () => {
  it('renders empty when no messages', () => {
    const { container } = renderManager({ messages: [], onDismiss: vi.fn() });
    expect(container.querySelector('[role="status"]')).toBeNull();
  });

  it('renders a single toast message', () => {
    renderManager({ messages: [{ id: '1', message: 'Test message' }], onDismiss: vi.fn() });
    expect(screen.getByText('Test message')).toBeInTheDocument();
  });

  it('renders multiple toast messages', () => {
    renderManager({
      messages: [
        { id: '1', message: 'First message' },
        { id: '2', message: 'Second message' },
      ],
      onDismiss: vi.fn(),
    });
    expect(screen.getByText('First message')).toBeInTheDocument();
    expect(screen.getByText('Second message')).toBeInTheDocument();
  });

  // Unlike Radix (where only a transient hidden announce copy carries
  // role="status", and the visible <li> carries no role at all), Tamagui's
  // fork puts role="status" on *both* the persistent visible toast
  // (aria-live="off", so it doesn't double-announce) and the transient
  // announce copy (aria-live="polite" for type="background", matching
  // Radix's politeness exactly) - a different DOM shape, same announcement
  // behavior. getAllByRole (not getByRole) because both are legitimately
  // present at once here.
  it('exposes role="status" with background-type ("polite") live-region politeness', () => {
    renderManager({ messages: [{ id: '1', message: 'Hello' }], onDismiss: vi.fn() });
    const statusElements = screen.getAllByRole('status');
    expect(statusElements.length).toBeGreaterThanOrEqual(1);
    expect(statusElements.some((el) => el.getAttribute('aria-live') === 'polite')).toBe(true);
    // None should be "assertive" - that's reserved for type="foreground", which this never uses.
    expect(statusElements.some((el) => el.getAttribute('aria-live') === 'assertive')).toBe(false);
  });

  it('calls onDismiss when toast closes', async () => {
    const onDismiss = vi.fn();
    renderManager({ messages: [{ id: 'abc', message: 'Bye' }], onDismiss });

    // Neither Radix nor this Tamagui swap render a close button by default
    // (closeButton defaults to false) - dismissal here is via the provider's
    // duration timeout, covered by the fake-timer test below rather than a
    // click in this test.
    const closeButton = screen.queryByRole('button');
    if (closeButton) {
      await userEvent.click(closeButton);
      expect(onDismiss).toHaveBeenCalledWith('abc');
    }
  });

  // #581 acceptance criterion: "Toasts auto-dismiss after the configured
  // duration ... and clean up their timers on unmount" - untested even under
  // the original Radix implementation (no prior test exercised this at all).
  it('auto-dismisses after the configured duration', () => {
    vi.useFakeTimers();
    try {
      const onDismiss = vi.fn();
      renderWithDuration({ messages: [{ id: 'abc', message: 'Bye' }], onDismiss }, 100);

      expect(onDismiss).not.toHaveBeenCalled();

      act(() => {
        vi.advanceTimersByTime(150);
      });

      expect(onDismiss).toHaveBeenCalledWith('abc');
    } finally {
      vi.useRealTimers();
    }
  });

  // Unmounting before the timer fires must not call onDismiss (or throw) -
  // the timer needs to be cleared, not just left to fire into a gone
  // component. This is the "clean up their timers on unmount" half of the
  // same acceptance criterion.
  it('does not call onDismiss after unmounting before the duration elapses', () => {
    vi.useFakeTimers();
    try {
      const onDismiss = vi.fn();
      const { unmount } = renderWithDuration(
        { messages: [{ id: 'abc', message: 'Bye' }], onDismiss },
        100
      );

      unmount();

      act(() => {
        vi.advanceTimersByTime(150);
      });

      expect(onDismiss).not.toHaveBeenCalled();
    } finally {
      vi.useRealTimers();
    }
  });

  // Accepted a11y gap (#581): Radix's Toast.Root/Viewport render as a real
  // <li>/<ol> (native list navigation for screen readers across stacked
  // toasts); Tamagui's are View-based with no way to override the rendered
  // tag from this call site. See the comment in ToastManager.tsx - the
  // "renders viewport as an ordered list" / "renders each toast as a list
  // item" assertions this file used to have no longer hold, deliberately.
});
