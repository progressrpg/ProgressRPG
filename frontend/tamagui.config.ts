// Tamagui config for the RN/Expo migration (epic #578/#591, decided in
// #591). Built from @tamagui/config's default web preset; token values are
// Tamagui's stock ones for now, not the app's own SCSS scale (see
// src/styles/semantic/_colors.scss, _typography.scss). Each component
// ported onto Tamagui is expected to reconcile its own visual output
// against the SCSS original (see ProgressBar.tsx for the first instance);
// a shared token source of truth is tracked separately (#590).
import { config as defaultConfig } from '@tamagui/config';
import { createTamagui } from 'tamagui';

// @tamagui/config's stock `media` breakpoints (xs: 660, sm: 800, md: 1020...)
// don't match this app's own breakpoint scale (src/styles/base/_variables.scss:
// sm: 576, md: 768...) used by the SCSS `respond-to()` mixin. Overriding here
// so components ported from SCSS produce the same breakpoint behaviour as
// their originals, not Tamagui's defaults.
const config = createTamagui({
  ...defaultConfig,
  media: {
    ...defaultConfig.media,
    sm: { maxWidth: 576 },
    md: { maxWidth: 768 },
    // SCSS `respond-to($bp)` defaults to a min-width ("up") query, but
    // `respond-to($bp, down)` uses the *same* breakpoint name for a
    // max-width query instead. One Tamagui media key can only ever mean
    // one direction, so the two call-site directions for "md" can't share
    // a key the way the SCSS mixin lets them - `mdUp` is a second key for
    // the "up" case, needed by components with a min-width breakpoint.
    mdUp: { minWidth: 768 },
  },
});

export type Conf = typeof config;

declare module 'tamagui' {
  // eslint-disable-next-line @typescript-eslint/no-empty-object-type
  interface TamaguiCustomConfig extends Conf {}
}

export default config;
