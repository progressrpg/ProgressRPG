// PoC (Restyle): hard-case port, exercises apply-text-style ($text-button,
// incl. its `md` breakpoint) plus apply-button-variant
// (primary/secondary/danger) - the same component the Tamagui/Gluestack
// PoCs used for their hard case, for direct comparison. Original stays at
// ./Button.tsx; see .claude/plans/issue-restyle-poc.md for findings.
import React from 'react';
import { PressableBox, Text } from '../../restyle-components';

interface ButtonRestyleProps {
  children?: React.ReactNode;
  variant?: 'primary' | 'secondary' | 'danger';
  disabled?: boolean;
  onClick?: () => void;
}

export default function ButtonRestyle({
  children,
  variant = 'primary',
  disabled = false,
  onClick,
}: ButtonRestyleProps) {
  return (
    <PressableBox
      variant={variant}
      disabled={disabled}
      onPress={onClick}
      // PoC finding: react-native-web's Pressable sets no ARIA role at all
      // by default - not even role="button" - unlike a real HTML <button>
      // or Tamagui's Button (which does set role="button" automatically).
      // Needs this explicit opt-in on every interactive component built on
      // Pressable, confirmed via real DOM inspection (not assumed from
      // docs): omitting it produced a bare `<div tabindex="0">` with no
      // role attribute whatsoever.
      accessibilityRole="button"
      flexDirection="row"
      justifyContent="center"
      alignItems="center"
      paddingHorizontal="md"
      paddingVertical="xs"
      gap="xs"
      borderRadius="md"
      // @ts-expect-error PoC: cursor isn't in BoxProps' RN-only type union;
      // react-native-web does support it.
      cursor="pointer"
    >
      <Text
        variant="button"
        color={variant === 'secondary' ? 'buttonSecondaryText' : 'textOnDark'}
      >
        {children}
      </Text>
    </PressableBox>
  );
}
