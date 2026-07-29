// PoC (issue #629): Tamagui port of Button, the required "hard case"
// component - exercises apply-text-style ($text-button, incl. its `md`
// breakpoint) plus apply-button-variant (primary/secondary/danger).
// Original stays at ./Button.tsx for comparison; see
// .claude/plans/issue-629-tamagui-poc.md for findings.
import React from 'react';
import { Button as TamaguiButton, styled } from 'tamagui';

// Resolved output of this app's SCSS tokens (src/styles/semantic/_colors.scss
// $button-variants, $text-tone; _typography.scss $text-button) - hand-copied
// since Tamagui has no visibility into the SCSS token pipeline.
const ButtonFrame = styled(TamaguiButton, {
  name: 'Button',
  display: 'flex',
  justifyContent: 'center',
  alignItems: 'center',
  paddingVertical: '0.5rem',
  paddingHorizontal: '1rem',
  gap: '0.5rem',
  borderRadius: '1rem',
  borderWidth: 1,
  borderStyle: 'solid',
  borderColor: 'transparent',
  cursor: 'pointer',
  textAlign: 'center',
  fontFamily: 'Roboto, sans-serif',
  fontSize: '1rem',
  fontWeight: '400',
  lineHeight: 1.5,
  letterSpacing: 'normal',

  // $text-button's `md` layer (apply-text-style): font-size: 1.125rem at
  // min-width 768. Requires the `mdUp` media key added in tamagui.config.ts
  // - the config's own `md` means max-width here (see that file's comment).
  '$mdUp': {
    fontSize: '1.125rem',
  },

  variants: {
    // Named `appVariant`, not `variant` - Tamagui's own Button already
    // reserves `variant` for its built-in `'outlined'` style, so reusing
    // the app's naming (`variant="primary"`) collides with that.
    appVariant: {
      primary: {
        backgroundColor: '#007a32',
        color: '#fefefe',
        hoverStyle: { backgroundColor: 'rgb(0, 147.5, 60.45)' },
        pressStyle: { backgroundColor: 'rgb(0, 96.5, 39.55)' },
      },
      secondary: {
        backgroundColor: '#e7fff1',
        color: 'rgb(0, 96.5, 39.55)',
        borderColor: 'rgba(0, 122, 50, 0.35)',
        hoverStyle: {
          backgroundColor: 'rgb(205.5, 255, 226.125)',
          borderColor: 'rgba(0, 122, 50, 0.55)',
        },
        pressStyle: { backgroundColor: 'rgb(180, 255, 211.25)' },
      },
      danger: {
        backgroundColor: '#c62828',
        color: '#fefefe',
        hoverStyle: { backgroundColor: '#b71c1c' },
        pressStyle: { backgroundColor: '#8e0000' },
      },
    },
  } as const,

  defaultVariants: {
    appVariant: 'primary',
  },
});

interface ButtonTamaguiProps {
  children?: React.ReactNode;
  variant?: 'primary' | 'secondary' | 'danger';
  disabled?: boolean;
  onClick?: React.MouseEventHandler<HTMLButtonElement>;
}

export default function ButtonTamagui({
  children,
  variant = 'primary',
  disabled = false,
  onClick,
}: ButtonTamaguiProps) {
  return (
    <ButtonFrame appVariant={variant} disabled={disabled} onPress={onClick as never}>
      {children}
    </ButtonFrame>
  );
}
