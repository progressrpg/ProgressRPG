import React from 'react';
import classNames from 'classnames';
import { Tooltip as TamaguiTooltip, TooltipGroup } from 'tamagui';
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

// delayDuration/skipDelayDuration/disableHoverableContent all configured
// Radix's hover-intent delay-grouping - dead weight already since #568
// replaced hover-open with click/tap-to-toggle everywhere. Kept as accepted
// props (nothing downstream breaks passing them) and still threaded through
// to Tamagui's TooltipGroup for forward-compatibility, but none of them
// currently have an observable effect - there is no hover-to-open left for
// a delay to apply to. disableHoverableContent has no Tamagui equivalent at
// all (accepted, unused).
export function TooltipProvider({
  children,
  delayDuration = 250,
  skipDelayDuration = 100,
}: TooltipProviderProps): React.ReactElement {
  return (
    <TooltipGroup delay={{ open: delayDuration, close: delayDuration }} timeoutMs={skipDelayDuration}>
      {children}
    </TooltipGroup>
  );
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
  // Tracks whether the trigger's current focus came from our own
  // pointerdown handler below, so that handler and handleFocus don't both
  // try to decide the open state for the same interaction.
  const pointerDownRef = React.useRef(false);
  // Stable id linking the trigger to its tooltip content for
  // aria-describedby - see the note on cloning children below for why this
  // is done manually rather than left to Tamagui's Trigger.
  const contentId = React.useId();

  if (disabled || content === null || content === undefined || content === false) {
    return <>{children}</>;
  }

  // Tamagui's Tooltip hardcodes `hoverable: true` internally (Tooltip.tsx's
  // own useFloatingContext call) with no prop to opt out, and floating-ui's
  // own interaction-prop merging (@tamagui/floating's useInteractions:
  // "event handlers are chained (all run)") calls its hover handlers
  // unconditionally - verified directly: preventDefault() in our own
  // handler does NOT stop it the way it stopped Radix's hover-open, because
  // Radix's own composeEventHandlers checks event.defaultPrevented and
  // floating-ui's chaining here does not. So hover can still ask to open
  // via this onOpenChange callback; only ever accept closes through it, and
  // let *our own* handlers open the tooltip by calling setOpen(true)
  // directly, bypassing this callback entirely.
  const handleOpenChange = (next: boolean) => {
    if (next) return;
    setOpen(false);
  };

  // Tamagui's PopoverTrigger (which Tooltip.Trigger wraps) registers itself
  // in a DismissableBranch, exempting the trigger from being treated as
  // "outside" the open content - unlike Radix, where a second pointerdown
  // on an already-open trigger got caught by Radix's own outside-press
  // dismiss layer and closed it for us (see the old comment this replaces).
  // That closing-for-free doesn't happen here, so this toggles explicitly.
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

  // Hand-rolled fix for a confirmed Tamagui/@tamagui/popper bug (see #583,
  // filed upstream as tamagui/tamagui#4152): Popper's own internal
  // useFloating() instance resets FloatingOverrideContext to null around its
  // children, so the focus-aware interaction props Tooltip's `focus={{
  // enabled: true }}` would build never reach the real trigger DOM node -
  // Tab-focusing it silently does nothing in the upstream default path.
  // (Tamagui's TooltipContent also hardcodes the focus interaction hook off
  // entirely via `alwaysDisable={{ focus: true, ... }}`, so this isn't even
  // reachable by turning the prop on - it's disabled at the source.) Rather
  // than depend on that broken/disabled path at all, this component drives
  // `open` itself via its own onFocus handler passed directly to
  // Tooltip.Trigger, bypassing Tamagui's internal interaction-props system
  // entirely - the same fix the issue's own writeup names as one of the
  // options ("hand-roll the trigger's onFocus/onBlur to call the controlled
  // open setter directly"). Verified against Tooltip.test.tsx's real
  // Tab-focus case, not assumed from source reading alone.
  const handleFocus = (event: React.FocusEvent) => {
    event.preventDefault();
    if (!pointerDownRef.current) setOpen(true);
  };

  const handleBlur = () => {
    if (!pointerDownRef.current) setOpen(false);
  };

  // Tamagui's Popper takes a single floating-ui-style `placement` (e.g.
  // "top-start"), not Radix's separate side/align - compose the two public
  // props into that format. No dash suffix means center-aligned.
  const tamaguiPlacement = align === 'center' ? placement : `${placement}-${align}`;

  // Tamagui's Trigger (PopoverTrigger) always wraps children in its own
  // View - unlike Radix's asChild, there's no way to merge onto the child
  // directly - so aria-expanded/aria-describedby/data-state that Tamagui
  // sets on that wrapper land one level above the actual focusable element,
  // invisible to a screen reader focused on the real button (confirmed via
  // the rendered DOM, not assumed). Cloning children ourselves to carry
  // aria-describedby puts the association where assistive tech actually
  // looks: on the focused element itself.
  const triggerChild = React.cloneElement(
    children,
    { 'aria-describedby': open ? contentId : undefined } as React.Attributes
  );

  return (
    <TamaguiTooltip
      open={open}
      onOpenChange={handleOpenChange}
      placement={tamaguiPlacement as never}
      offset={sideOffset}
      stayInFrame={{ padding: 8 }}
    >
      <TamaguiTooltip.Trigger
        // display:contents on .trigger (Tooltip.module.scss) keeps
        // Tamagui's wrapper View out of layout/flex-item participation, so
        // it doesn't change how consumers' existing layouts around a
        // trigger behave.
        className={styles.trigger}
        onPointerDown={handlePointerDown}
        onFocus={handleFocus}
        onBlur={handleBlur}
      >
        {triggerChild}
      </TamaguiTooltip.Trigger>
      <TamaguiTooltip.Content
        unstyled
        id={contentId}
        className={classNames(styles.content, className)}
      >
        {content}
        {/* Tamagui's Arrow is a rotated square clipped by an outer frame,
            not Radix's SVG polygon - .arrow (SCSS) uses background-color,
            not the fill it used against Radix's <svg>. `unstyled` skips
            Tamagui's own default border/background so ours is the only one
            applied. */}
        <TamaguiTooltip.Arrow unstyled className={styles.arrow} size={9} />
      </TamaguiTooltip.Content>
    </TamaguiTooltip>
  );
}
