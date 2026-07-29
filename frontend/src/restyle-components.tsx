// PoC (Restyle): thin Box/Text/PressableBox factories bound to this app's
// theme, following Restyle's own documented pattern for custom
// variant-driven components (createRestyleComponent + createVariant,
// composed with the stock box restyle functions).
import { Pressable } from 'react-native';
import {
  createBox,
  createText,
  createRestyleComponent,
  createVariant,
  boxRestyleFunctions,
  type VariantProps,
} from '@shopify/restyle';
import type { Theme } from './restyle-theme';

export const Box = createBox<Theme>();
export const Text = createText<Theme>();

type PressableBoxProps = React.ComponentProps<typeof Pressable> &
  React.ComponentProps<typeof Box> &
  VariantProps<Theme, 'buttonVariants'>;

export const PressableBox = createRestyleComponent<PressableBoxProps, Theme>(
  [...boxRestyleFunctions, createVariant({ themeKey: 'buttonVariants' })],
  Pressable
);
