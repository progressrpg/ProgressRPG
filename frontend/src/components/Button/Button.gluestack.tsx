// PoC (issue #631): Gluestack/NativeWind port of Button, the required "hard
// case" component - exercises apply-text-style ($text-button, incl. its
// `md` breakpoint) plus apply-button-variant (primary/secondary/danger).
// Original stays at ./Button.tsx for comparison; see
// .claude/plans/issue-631-gluestack-poc.md for findings.
import React from 'react';
import { Pressable, Text, View } from 'react-native';
import { cssInterop } from 'nativewind';
import { createButton } from '@gluestack-ui/button';
import { withStates } from '@gluestack-ui/nativewind-utils/withStates';
import { tva } from '@gluestack-ui/nativewind-utils/tva';

cssInterop(Pressable, { className: 'style' });
cssInterop(Text, { className: 'style' });

// `createButton` is @gluestack-ui/button's headless primitive: it wraps
// whatever "styled" Root component is passed in with hover/press/focus
// state management (via @react-native-aria), then hands that state back as
// a `states` prop and `dataSet` attributes - `withStates` is what actually
// resolves the `data-[state=value]:class` tokens below against that
// `states` object, purely in JS (not real CSS attribute selectors - see
// findings doc).
//
// PoC finding: `createButton` needs all 5 parts (`Root`, `Text`, `Group`,
// `Spinner`, `Icon`), not just a single styled component - passing one
// component directly (matching the inner factory function's own signature
// in Button.tsx, which reads misleadingly like the whole public API)
// silently produced `Root: undefined` and a "got: undefined" render error,
// only caught by inspecting the actual index.tsx wiring.
const UIButton = createButton({
  Root: withStates(Pressable),
  Text,
  Group: View,
  Spinner: View,
  Icon: View,
});

// PoC note: unlike #629's Tamagui port, Tailwind's *default* `md` breakpoint
// (768px) already matches this app's own SCSS breakpoint
// (src/styles/base/_variables.scss) exactly for the "up" direction
// `$text-button` needs - no custom breakpoint config was needed here, in
// contrast to Tamagui's stock preset (`md: 1020`) requiring an override.
const buttonStyle = tva({
  base: 'flex flex-row justify-center items-center rounded-2xl border border-solid border-transparent px-4 py-2 gap-2 font-sans text-base font-normal leading-normal cursor-pointer md:text-lg',
  variants: {
    appVariant: {
      primary:
        'bg-[#007a32] text-white data-[hover=true]:bg-[rgb(0,147.5,60.45)] data-[active=true]:bg-[rgb(0,96.5,39.55)]',
      secondary:
        'bg-[#e7fff1] text-[rgb(0,96.5,39.55)] border-[rgba(0,122,50,0.35)] data-[hover=true]:bg-[rgb(205.5,255,226.125)] data-[active=true]:bg-[rgb(180,255,211.25)]',
      danger:
        'bg-[#c62828] text-white data-[hover=true]:bg-[#b71c1c] data-[active=true]:bg-[#8e0000]',
    },
  },
});

interface ButtonGluestackProps {
  children?: React.ReactNode;
  variant?: 'primary' | 'secondary' | 'danger';
  disabled?: boolean;
  onClick?: () => void;
}

export default function ButtonGluestack({
  children,
  variant = 'primary',
  disabled = false,
  onClick,
}: ButtonGluestackProps) {
  return (
    <UIButton
      className={buttonStyle({ appVariant: variant })}
      isDisabled={disabled}
      onPress={onClick}
    >
      <UIButton.Text className="text-inherit">{children}</UIButton.Text>
    </UIButton>
  );
}
