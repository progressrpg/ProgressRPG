// PoC (issue #631): Gluestack/NativeWind port of Tooltip, swapping the
// underlying primitive as required by the spike scope (same component
// #579's `@rn-primitives/tooltip` PoC and #629's Tamagui PoC both swapped,
// for direct comparison). Original stays at ./Tooltip.tsx; see
// .claude/plans/issue-631-gluestack-poc.md for findings.
//
// Unlike either prior PoC, @gluestack-ui/tooltip's root already wires
// hover, focus/blur, and Escape-to-close internally (via
// @react-native-aria/interactions' `useKeyboardDismissable`) - no extra
// opt-in flag needed the way Tamagui's PoC needed `focus={{enabled:true}}`.
//
// PoC finding: this component renders nothing at all - not a blank tooltip,
// the portal target simply never mounts - unless an `OverlayProvider` (from
// `@gluestack-ui/overlay`, re-exporting `@react-native-aria/overlays`) is
// present somewhere in the tree above it. `onOpen`/`onClose` still fire
// correctly without one (confirmed via a diagnostic), so this fails
// silently: the component *looks* like it's toggling state correctly with
// no console error, while the DOM never gets a `role="tooltip"` node at
// all. A real adoption needs `<OverlayProvider>` mounted once at the app
// root - same shape as Tamagui's `<TamaguiProvider>` or the current app's
// own `<TooltipProvider>`, just entirely undocumented in the primitive's
// own type signature.
import React from 'react';
import { View, Text } from 'react-native';
import { cssInterop } from 'nativewind';
import { createTooltip } from '@gluestack-ui/tooltip';

cssInterop(View, { className: 'style' });
cssInterop(Text, { className: 'style' });

const UITooltip = createTooltip({
  Root: View,
  // PoC note: TooltipContent's HOC handles all positioning itself (via
  // @react-native-aria/overlays' `useOverlayPosition`) - the styled
  // component passed in just needs to render its `style`/`children`, no
  // placement math needed here (unlike #629's Tamagui port, which needed
  // its own transform-origin/side CSS per placement).
  Content: View,
  Text,
});

type TooltipPlacement = 'top' | 'bottom' | 'left' | 'right';

interface TooltipProps {
  children: React.ReactElement;
  content: React.ReactNode;
  placement?: TooltipPlacement;
  disabled?: boolean;
}

export default function TooltipGluestack({
  children,
  content,
  placement = 'top',
  disabled = false,
}: TooltipProps): React.ReactElement {
  if (disabled || content === null || content === undefined || content === false) {
    return <>{children}</>;
  }

  return (
    <UITooltip
      placement={placement}
      openDelay={0}
      closeDelay={0}
      trigger={(triggerProps: Record<string, unknown>) =>
        React.cloneElement(children, triggerProps)
      }
    >
      <UITooltip.Content className="z-50 border border-solid border-[rgba(0,122,50,0.22)] rounded-lg bg-[rgba(26,26,26,0.96)] px-2 py-1 shadow-lg">
        <UITooltip.Text className="text-white text-sm leading-snug">{content}</UITooltip.Text>
      </UITooltip.Content>
    </UITooltip>
  );
}
