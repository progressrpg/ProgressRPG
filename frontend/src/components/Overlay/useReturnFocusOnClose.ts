import { useState } from 'react';

/**
 * Tamagui's Dialog/AlertDialog restore focus to a `Trigger` element when the
 * overlay closes - but Modal and AlertDialog have no `Trigger` in their tree
 * (they're driven by mount and by a controlled `open` prop instead, see
 * #582), so `context.triggerRef` is always empty and Tamagui's own restore
 * silently no-ops.
 *
 * This captures whatever had focus right before the overlay opened, and
 * returns an `onCloseAutoFocus` handler that restores it there instead.
 * Captured via the "adjust state during render" pattern (react.dev's
 * documented way to derive state from a changing prop), not a ref mutation
 * or an effect - it needs to run before FocusScope's own mount-time
 * auto-focus (a descendant effect that would otherwise steal focus first),
 * and effects run children-before-parents, so an effect here would already
 * be too late.
 */
export function useReturnFocusOnClose(open: boolean) {
  const [wasOpen, setWasOpen] = useState(false);
  const [returnFocusTarget, setReturnFocusTarget] = useState<HTMLElement | null>(null);

  if (open && !wasOpen) {
    setWasOpen(true);
    setReturnFocusTarget((document.activeElement as HTMLElement | null) ?? null);
  } else if (!open && wasOpen) {
    setWasOpen(false);
  }

  return function onCloseAutoFocus(event: Event) {
    event.preventDefault();
    returnFocusTarget?.focus?.();
  };
}
