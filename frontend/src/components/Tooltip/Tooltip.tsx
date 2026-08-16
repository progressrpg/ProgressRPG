import React from 'react';
import classNames from 'classnames';
import { Tooltip as TooltipPrimitive, type TamaguiElement } from 'tamagui';
import styles from './Tooltip.module.scss';

type TooltipPlacement = 'top' | 'bottom' | 'left' | 'right';
type TooltipAlign = 'start' | 'center' | 'end';

interface TooltipProviderProps {
  children: React.ReactNode;
  delayDuration?: number;
  skipDelayDuration?: number;
  disableHoverableContent?: boolean;
}

interface TooltipProps {
  children: React.ReactElement;
  content: React.ReactNode;
  placement?: TooltipPlacement;
  align?: TooltipAlign;
  sideOffset?: number;
  className?: string;
  disabled?: boolean;
}

/**
 * Radix's `Provider` grouped sibling tooltips under a shared hover-delay
 * timer. Tamagui's `Tooltip` needs no such ambient ancestor - each one is
 * self-contained - and #568 already made hover a no-op for opening (see
 * below), so there's no delay behaviour left to group. Kept as a passthrough,
 * accepting the same props, purely so call sites and tests don't need to
 * change (#582-style API-compatibility).
 */
export function TooltipProvider({ children }: TooltipProviderProps): React.ReactElement {
  return <>{children}</>;
}

function toTamaguiPlacement(placement: TooltipPlacement, align: TooltipAlign) {
  return align === 'center' ? placement : (`${placement}-${align}` as const);
}

// The DOM events React derives its synthetic onMouseEnter/onMouseLeave/
// onMouseMove from. React delegates a *single* listener per type at the
// app root rather than attaching one per element, and for the two
// non-bubbling ones (mouseenter/mouseleave) it doesn't listen for those
// directly at all - it listens for the bubbling mouseover/mouseout and
// derives enter/leave transitions itself. Pointer variants are included
// since React treats them as an equivalent source on pointer-capable
// browsers.
const HOVER_SOURCE_EVENT_TYPES = [
  'mouseover',
  'mouseout',
  'mousemove',
  'pointerover',
  'pointerout',
  'pointermove',
];

/**
 * Tamagui's Tooltip hardcodes `hoverable: true` in its floating-ui
 * interaction context, with no prop to turn it off - `useHover` (from
 * `@tamagui/floating`) exposes an `onMouseMove` *React prop* via
 * `getReferenceProps()`, which `asChild` merges onto the trigger's real
 * element (winning over any same-named prop we pass, the same "parent
 * wins" merge #582 hit with Dialog.Title's aria-label). That prop is
 * dispatched through React's own delegated root listener, not a listener
 * on the trigger itself, so a same-named prop can't pre-empt it. React
 * doesn't listen for 'mouseenter'/'mouseleave' directly either (they don't
 * bubble) - it derives its synthetic enter/leave from the bubbling
 * 'mouseover'/'mouseout' instead. Capturing those (plus 'mousemove' and the
 * pointer equivalents, since React treats pointer events as an equivalent
 * hover source) at `document` - an ancestor of React's root container -
 * pre-empts all of it: capture-phase listeners on an ancestor always run
 * before React's own listener on the root container ever sees the event.
 * Verified manually against a real browser (this interaction falls outside
 * what `npm run test:storybook`/`test:a11y` can run in this sandbox - see
 * #583's PR description).
 */
function useSuppressHoverOpen(triggerRef: React.RefObject<TamaguiElement | null>) {
  React.useEffect(() => {
    const isInTrigger = (event: Event) =>
      event.target instanceof Node &&
      ((triggerRef.current as HTMLElement | null)?.contains(event.target) ?? false);
    const stop = (event: Event) => {
      if (isInTrigger(event)) event.stopPropagation();
    };
    for (const type of HOVER_SOURCE_EVENT_TYPES) document.addEventListener(type, stop, true);
    return () => {
      for (const type of HOVER_SOURCE_EVENT_TYPES) document.removeEventListener(type, stop, true);
    };
  }, [triggerRef]);
}

/**
 * Use tooltips only for supplementary context. The trigger must remain a
 * focusable interactive element, and any essential information should stay
 * available without requiring hover or focus.
 *
 * Click/tap-to-toggle on both desktop and mobile (see #568): hover never
 * opens the tooltip, and clicking/tapping the trigger again - or anywhere
 * else - closes it.
 */
export default function Tooltip({
  children,
  content,
  placement = 'top',
  align = 'center',
  sideOffset = 8,
  className,
  disabled = false,
}: TooltipProps): React.ReactElement {
  const [open, setOpen] = React.useState(false);
  const triggerRef = React.useRef<TamaguiElement | null>(null);
  const contentRef = React.useRef<TamaguiElement | null>(null);
  // Tracks whether the trigger's current focus came from our own
  // pointerdown handler below, so that handler and handleFocusCapture don't
  // both try to decide the open state for the same interaction.
  const pointerDownRef = React.useRef(false);

  useSuppressHoverOpen(triggerRef);

  // Closing over outside-click and Escape ourselves, driven by real DOM
  // listeners, is more reliable here than leaning on Tamagui's own dismiss
  // wiring (untested/unclear for Tooltip content, unlike the Dismissable
  // layer #582 could rely on for Modal/AlertDialog) - and #568 wants a click
  // anywhere else, including elements with no tooltip of their own, to
  // close it, which is exactly what a document-level listener gives for
  // free.
  React.useEffect(() => {
    if (!open) return;
    const handlePointerDownOutside = (event: PointerEvent) => {
      const target = event.target as Node | null;
      if (!target) return;
      if ((triggerRef.current as HTMLElement | null)?.contains(target)) return;
      if ((contentRef.current as HTMLElement | null)?.contains(target)) return;
      setOpen(false);
    };
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setOpen(false);
    };
    document.addEventListener('pointerdown', handlePointerDownOutside, true);
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('pointerdown', handlePointerDownOutside, true);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [open]);

  if (disabled || content === null || content === undefined || content === false) {
    return <>{children}</>;
  }

  // The sole place we ever *open* the tooltip via pointer interaction - a
  // pointerdown on an already-open trigger toggles it closed directly.
  const handlePointerDown = (event: React.PointerEvent) => {
    event.preventDefault();
    pointerDownRef.current = true;
    document.addEventListener(
      'pointerup',
      () => {
        pointerDownRef.current = false;
      },
      { once: true }
    );
    setOpen((wasOpen) => !wasOpen);
  };

  // preventDefault() on pointerdown doesn't stop the resulting click event
  // for mouse pointers (only for touch, where it suppresses the
  // compatibility click outright), so left unhandled this would otherwise
  // reach any onClick a consumer's own child sets.
  const handleClick = (event: React.MouseEvent) => {
    event.preventDefault();
  };

  // Capture-phase - unlike onMouseEnter/onMouseLeave above, React (and thus
  // the DOM node Trigger's `asChild` clones onto) does accept an
  // onFocusCapture prop, even though Tamagui's own Trigger prop types don't
  // list it, so this one can stay a normal prop rather than needing a raw
  // DOM listener; running before Tamagui's own (broken - see
  // #583/tamagui/tamagui#4152) bubble-phase onFocus keeps our decision
  // authoritative either way.
  const handleFocusCapture = (event: React.FocusEvent) => {
    event.stopPropagation();
    if (!pointerDownRef.current) setOpen(true);
  };
  const focusCaptureProp = { onFocusCapture: handleFocusCapture };

  return (
    <TooltipPrimitive
      open={open}
      onOpenChange={setOpen}
      placement={toTamaguiPlacement(placement, align)}
      offset={sideOffset}
      allowFlip
      stayInFrame={{ padding: 8 }}
    >
      <TooltipPrimitive.Trigger
        ref={triggerRef}
        asChild
        className={styles.trigger}
        onPointerDown={handlePointerDown}
        onClick={handleClick}
        {...focusCaptureProp}
      >
        {children}
      </TooltipPrimitive.Trigger>
      <TooltipPrimitive.Content
        ref={contentRef}
        unstyled
        className={classNames(styles.content, className)}
      >
        {content}
        <TooltipPrimitive.Arrow unstyled className={styles.arrow} width={10} height={6} />
      </TooltipPrimitive.Content>
    </TooltipPrimitive>
  );
}
