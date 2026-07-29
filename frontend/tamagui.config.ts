// PoC (issue #629): minimal Tamagui config, built from @tamagui/config's
// default web preset. A real adoption would replace these tokens with the
// app's own scale (see src/styles/semantic/_colors.scss, _typography.scss)
// instead of Tamagui's stock ones - out of scope for this spike.
import { config as defaultConfig } from '@tamagui/config'
import { createTamagui } from 'tamagui'

// PoC (issue #629): @tamagui/config's stock `media` breakpoints (xs: 660,
// sm: 800, md: 1020...) don't match this app's own breakpoint scale
// (src/styles/base/_variables.scss: sm: 576, md: 768...) used by the SCSS
// `respond-to()` mixin. A real adoption would need this alignment anyway -
// overriding here so the ported components below produce the same
// breakpoint behavior as their SCSS originals, not Tamagui's defaults.
const config = createTamagui({
  ...defaultConfig,
  media: {
    ...defaultConfig.media,
    sm: { maxWidth: 576 },
    md: { maxWidth: 768 },
    // PoC finding: SCSS `respond-to($bp)` defaults to a min-width ("up")
    // query, but `respond-to($bp, down)` (used by e.g. OnlineCountBadge)
    // uses the *same* breakpoint name for a max-width query instead. One
    // Tamagui media key can only ever mean one direction, so the two
    // call-site directions for "md" can't share a key the way the SCSS
    // mixin lets them - `mdUp` is a second key for the "up" case (used by
    // Button's $text-button breakpoint below).
    mdUp: { minWidth: 768 },
  },
})

export type Conf = typeof config

declare module 'tamagui' {
  // eslint-disable-next-line @typescript-eslint/no-empty-object-type
  interface TamaguiCustomConfig extends Conf {}
}

export default config
