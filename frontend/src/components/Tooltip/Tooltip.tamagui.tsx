// PoC (issue #629): Tamagui port of Tooltip, swapping the underlying
// primitive as required by the spike scope (direct comparison against
// #579's @rn-primitives/tooltip PoC on branch
// claude/rn-primitives-library-4ny4sa). Original stays at ./Tooltip.tsx;
// see .claude/plans/issue-629-tamagui-poc.md for findings.
//
// Unlike @rn-primitives/tooltip, Tamagui's Tooltip *does* expose a
// controlled `open` prop directly on the root - so, unlike the #579 PoC,
// no ref/imperative-open workaround is needed here to keep this a drop-in
// replacement for the app's existing controlled-open call sites.
import React from 'react';
import { Tooltip as TamaguiTooltip } from 'tamagui';

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

// PoC note: like @rn-primitives/tooltip, Tamagui's Tooltip has no top-level
// `Provider` part either - `delay`/`restMs` are props on each `Tooltip`
// instance. Same context-shim approach as the #579 PoC to keep the app's
// single-Provider-at-the-root public API unchanged.
const TooltipProviderContext = React.createContext<Required<Omit<TooltipProviderProps, 'children'>>>({
  delayDuration: 250,
  skipDelayDuration: 100,
  disableHoverableContent: true,
});

export function TooltipProviderTamagui({
  children,
  delayDuration = 250,
  skipDelayDuration = 100,
  disableHoverableContent = true,
}: TooltipProviderProps): React.ReactElement {
  return (
    <TooltipProviderContext.Provider
      value={{ delayDuration, skipDelayDuration, disableHoverableContent }}
    >
      {children}
    </TooltipProviderContext.Provider>
  );
}

export default function TooltipTamagui({
  children,
  content,
  placement = 'top',
  sideOffset = 8,
  disabled = false,
}: TooltipProps): React.ReactElement {
  const providerConfig = React.useContext(TooltipProviderContext);
  const [open, setOpen] = React.useState(false);

  if (disabled || content === null || content === undefined || content === false) {
    return <>{children}</>;
  }

  return (
    <TamaguiTooltip
      open={open}
      onOpenChange={setOpen}
      placement={placement}
      offset={sideOffset}
      delay={{ open: providerConfig.delayDuration, close: providerConfig.skipDelayDuration }}
      restMs={0}
      // PoC finding: unlike Radix (focus-to-show is built in, no opt-in),
      // Tamagui's Tooltip only opens on hover unless `focus.enabled` is set
      // explicitly - easy to miss since nothing errors, the tooltip just
      // silently never opens on Tab.
      focus={{ enabled: true }}
    >
      <TamaguiTooltip.Trigger asChild>{children}</TamaguiTooltip.Trigger>
      {/* No explicit role="tooltip" here - Tamagui already sets it on the
          floating portal wrapper it renders around this Content; adding
          our own creates a second element with the same role (found via
          the diagnostic below), which broke role-based queries. */}
      <TamaguiTooltip.Content
        enterStyle={{ opacity: 0 }}
        exitStyle={{ opacity: 0 }}
        opacity={1}
        backgroundColor="rgba(26, 26, 26, 0.96)"
        borderColor="rgba(0, 122, 50, 0.22)"
        borderWidth={1}
        borderRadius="0.5rem"
        paddingVertical="0.25rem"
        paddingHorizontal="0.5rem"
        maxWidth="20rem"
        pointerEvents="none"
      >
        <TamaguiTooltip.Arrow />
        <span style={{ color: '#fefefe', fontSize: '0.875rem', lineHeight: 1.4 }}>
          {content}
        </span>
      </TamaguiTooltip.Content>
    </TamaguiTooltip>
  );
}
