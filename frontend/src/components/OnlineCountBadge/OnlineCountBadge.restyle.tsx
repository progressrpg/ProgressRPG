// PoC (Restyle): trivial-case port, matching the same component the
// Tamagui/Gluestack PoCs used for their trivial case. Original stays at
// ./OnlineCountBadge.tsx; see .claude/plans/issue-restyle-poc.md for
// findings.
import React from 'react';
import { useAuth } from '../../context/AuthContext';
import { useOnlineCount } from '../../context/OnlineCountContext';
import { Box, Text } from '../../restyle-components';

export default function OnlineCountBadgeRestyle() {
  const { isAuthenticated } = useAuth();
  const { onlinePlayerCount } = useOnlineCount();

  if (!isAuthenticated) {
    return null;
  }

  return (
    <Box
      position="fixed"
      left={16}
      // PoC finding: Restyle's breakpoints (like Tamagui's stock `md`) are a
      // single min-width scale - the SCSS original's `respond-to(md, down)`/
      // `respond-to(sm, down)` ("below md, then below sm, push further up")
      // has no built-in "max-width" equivalent to opt into; hand-rolled via
      // plain responsive `bottom` values keyed by this app's own breakpoint
      // widths instead of relying on any built-in down-direction API.
      bottom={{ phone: 144, sm: 128, md: 16 }}
      backgroundColor="background"
      borderWidth={1}
      borderColor="borderPrimary"
      borderRadius="md"
      paddingHorizontal="sm"
      paddingVertical="xs"
      // @ts-expect-error PoC: position:'fixed' + zIndex aren't in BoxProps'
      // strict RN-only type union; react-native-web does support both.
      zIndex={1000}
      accessibilityRole="text"
      accessibilityLiveRegion="polite"
    >
      <Text variant="defaults">
        <Text accessibilityElementsHidden importantForAccessibility="no-hide-descendants">
          🟢{' '}
        </Text>
        {Math.max(1, onlinePlayerCount)} players online
      </Text>
    </Box>
  );
}
