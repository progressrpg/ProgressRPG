// PoC (issue #631): Gluestack/NativeWind port of OnlineCountBadge, the
// "trivial / styling-only" component required by the spike scope. Original
// stays at ./OnlineCountBadge.tsx for comparison; see
// .claude/plans/issue-631-gluestack-poc.md for findings.
import React from 'react';
import { View } from 'react-native';
import { cssInterop } from 'nativewind';
import { useAuth } from '../../context/AuthContext';
import { useOnlineCount } from '../../context/OnlineCountContext';

// PoC note: react-native-web's View does NOT understand Tailwind classes on
// its own - `cssInterop` is NativeWind's opt-in (per-component, not global)
// mechanism that maps a `className` prop into RN style objects at runtime.
// This is the scoped alternative to setting `jsxImportSource: 'nativewind'`
// globally in vite.config.ts, which was tried first and reverted after
// measuring its cost (see vite.config.ts comment + findings doc).
cssInterop(View, { className: 'style' });

export default function OnlineCountBadgeGluestack() {
  const { isAuthenticated } = useAuth();
  const { onlinePlayerCount } = useOnlineCount();

  if (!isAuthenticated) {
    return null;
  }

  return (
    <View
      // Values match the resolved SCSS tokens the original component uses
      // (src/styles/semantic/_colors.scss, base/_variables.scss) - same
      // hand-copy caveat as #629's Tamagui PoC: Tailwind's default theme
      // scale has no visibility into this app's own token pipeline, so a
      // real port needs `tailwind.config.js` theme customization (see #590),
      // not ad-hoc arbitrary-value classes like below.
      className="fixed left-4 bottom-4 z-10 bg-white border border-solid border-[#007a32] rounded-lg px-2 py-1 font-sans text-base"
      {...({ role: 'status', 'aria-live': 'polite' } as Record<string, string>)}
    >
      <span aria-hidden="true">🟢 </span>
      {Math.max(1, onlinePlayerCount)} players online
    </View>
  );
}
