// Tamagui config for the RN/Expo migration (epic #578/#591, decided in
// #591). Colour and space tokens and the breakpoints come from the app's own
// design tokens (src/tokens/, #592) - the same source the SCSS layer is
// generated from - so Tamagui and SCSS can't drift apart. Still built on
// @tamagui/config's default web preset for what the app has no
// Tamagui-shaped equivalent of yet: the `size` scale (Tamagui's internal
// component dimensions, whose keys radius/zIndex must also use - so those
// stay stock too), themes and animations.
//
// Fonts also stay stock for now, deliberately: Tamagui's wrapper elements
// set the inherited font, and AlertDialog's Title/Description render
// Tamagui's own heading/body styles, so swapping in the app's typography is
// a visible change (font family in portals, and the AlertDialog title from
// 32px to 18px) rather than a token move. That's a design decision for its
// own change, not part of this appearance-preserving one.
import { config as defaultConfig } from '@tamagui/config';
import { createTamagui, createTokens } from 'tamagui';

import { breakpoints, color, scale, semanticColor, spacing } from './src/tokens/index.ts';

// Flattened for Tamagui's single-level colour tokens: $primary, $primary400,
// $neutral900, $colorTextBody... The mapped type keeps the scale keys typed,
// so `$primary400` type-checks as a token.
type Scale = typeof scale;
type ScaleTokens = {
  [Name in keyof Scale & string as `${Name}${keyof Scale[Name] & string}`]: string;
};

const scaleTokens = Object.fromEntries(
  Object.entries(scale).flatMap(([name, steps]) =>
    Object.entries(steps).map(([step, value]) => [`${name}${step}`, value]),
  ),
) as ScaleTokens;

const colorTokens = { ...color, ...scaleTokens, ...semanticColor };

// Tamagui requires space/radius/zIndex keys to be a subset of the `size`
// token keys, which stay stock ($0-$20, $true) - so the app's named spacing
// scale is keyed by step instead: $1 = xs ... $7 = 3xl, in scale order.
// `true` is the default Tamagui falls back to.
const space = {
  0: 0,
  ...Object.fromEntries(Object.values(spacing).map((px, i) => [i + 1, px])),
  true: spacing.md,
};

const tokens = createTokens({
  ...defaultConfig.tokens,
  color: colorTokens,
  space,
});

const config = createTamagui({
  ...defaultConfig,
  tokens,
  // @tamagui/config's stock `media` breakpoints (xs: 660, sm: 800, md: 1020...)
  // don't match this app's own breakpoint scale (the SCSS `respond-to()` mixin
  // uses the same tokens: sm: 576, md: 768...). Overriding here so components
  // ported from SCSS produce the same breakpoint behaviour as their originals,
  // not Tamagui's defaults.
  media: {
    ...defaultConfig.media,
    sm: { maxWidth: breakpoints.sm },
    md: { maxWidth: breakpoints.md },
    // SCSS `respond-to($bp)` defaults to a min-width ("up") query, but
    // `respond-to($bp, down)` uses the *same* breakpoint name for a
    // max-width query instead. One Tamagui media key can only ever mean
    // one direction, so the two call-site directions for "md" can't share
    // a key the way the SCSS mixin lets them - `mdUp` is a second key for
    // the "up" case, needed by components with a min-width breakpoint.
    mdUp: { minWidth: breakpoints.md },
  },
});

export type Conf = typeof config;

declare module 'tamagui' {
  // eslint-disable-next-line @typescript-eslint/no-empty-object-type
  interface TamaguiCustomConfig extends Conf {}
}

export default config;
