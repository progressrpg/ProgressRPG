// PoC (issue #629): Tamagui port of OnlineCountBadge, the "trivial /
// styling-only" component required by the spike scope. Original stays at
// ./OnlineCountBadge.tsx for comparison; see
// .claude/plans/issue-629-tamagui-poc.md for findings.
import React from 'react';
import { styled, View } from 'tamagui';
import { useAuth } from '../../context/AuthContext';
import { useOnlineCount } from '../../context/OnlineCountContext';

// Values below are the resolved output of the SCSS tokens the original
// component uses (src/styles/semantic/_colors.scss, base/_variables.scss),
// hand-copied since Tamagui has no visibility into the SCSS token
// pipeline - a real port would need its own token source of truth (see
// tamagui.config.ts note on #590).
const Badge = styled(View, {
  position: 'fixed',
  left: '1rem',
  bottom: '1rem',
  zIndex: 10,
  backgroundColor: 'hsl(145, 100%, 100%)', // $color-bg (out-of-range lightness clamps to white)
  borderWidth: 1,
  borderStyle: 'solid',
  borderColor: '#007a32', // $color-border-primary
  borderRadius: '0.5rem', // $border-radius
  paddingVertical: '0.25rem',
  paddingHorizontal: '0.5rem',
  fontFamily: 'Roboto, sans-serif',
  fontSize: '1rem',
  fontWeight: '400',
  lineHeight: 1.5,
});

export default function OnlineCountBadgeTamagui() {
  const { isAuthenticated } = useAuth();
  const { onlinePlayerCount } = useOnlineCount();

  if (!isAuthenticated) {
    return null;
  }

  return (
    <Badge aria-live="polite" role="status">
      <span aria-hidden="true">🟢 </span>
      {Math.max(1, onlinePlayerCount)} players online
    </Badge>
  );
}
