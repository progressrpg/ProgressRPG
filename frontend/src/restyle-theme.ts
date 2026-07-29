// PoC (Restyle vs Tamagui/Gluestack/@rn-primitives): minimal Restyle theme,
// hand-copied from this app's own SCSS tokens (src/styles/semantic/_colors.scss
// $button-variants/$text-tone, _typography.scss $text-button,
// base/_variables.scss breakpoints) the same way the Tamagui PoC had to -
// Restyle has no more visibility into the SCSS pipeline than Tamagui did.
import { createTheme } from '@shopify/restyle';

const theme = createTheme({
  colors: {
    buttonPrimaryBg: '#007a32',
    buttonPrimaryHover: 'rgb(0, 147.5, 60.45)',
    buttonPrimaryActive: 'rgb(0, 96.5, 39.55)',
    buttonSecondaryBg: '#e7fff1',
    buttonSecondaryText: 'rgb(0, 96.5, 39.55)',
    buttonSecondaryBorder: 'rgba(0, 122, 50, 0.35)',
    buttonDangerBg: '#c62828',
    buttonDangerHover: '#b71c1c',
    buttonDangerActive: '#8e0000',
    textOnDark: '#fefefe',
    borderPrimary: '#c9c9c9',
    background: '#ffffff',
    // PoC finding: unlike Tamagui (which accepts raw CSS literals alongside
    // token references), Restyle's themed properties (backgroundColor,
    // borderColor, color, ...) only accept values registered in the theme's
    // own map - passing a raw literal like 'transparent' directly throws
    // `Value 'transparent' does not exist in theme['colors']` at runtime,
    // confirmed via a real Playwright pageerror, not assumed from docs.
    // Needs its own token even for values with no real "brand" meaning.
    transparent: 'transparent',
  },
  spacing: {
    xs: 4,
    sm: 8,
    md: 16,
  },
  borderRadii: {
    sm: 8,
    md: 16,
  },
  // PoC finding, checked directly against Restyle's own types
  // (BaseTheme['breakpoints'] -> Breakpoint = number, single value, no
  // direction flag): breakpoints here are a plain min-width scale, same
  // single-direction constraint the Tamagui PoC hit with its `md`/`mdUp`
  // split - `respond-to($bp, down)` (used by OnlineCountBadge) has no direct
  // equivalent and needs to be hand-rolled (see OnlineCountBadge.restyle.tsx).
  breakpoints: {
    phone: 0,
    sm: 576,
    md: 768,
  },
  textVariants: {
    button: {
      fontFamily: 'Roboto, sans-serif',
      fontWeight: '400',
      lineHeight: 24,
      letterSpacing: 0,
      textTransform: 'none',
      // PoC finding: responsive values are plain objects keyed by breakpoint
      // name, applied directly as a prop value - matches this library's docs,
      // no extra API to opt into (contrast with Tamagui's `$mdUp` media-key
      // syntax, which - per the corrected Tamagui PoC finding - does work,
      // just needed real debugging to find that out).
      fontSize: { phone: 16, md: 18 },
    },
    defaults: {
      fontFamily: 'Roboto, sans-serif',
      fontSize: 16,
      fontWeight: '400',
      lineHeight: 24,
    },
  },
  buttonVariants: {
    primary: {
      backgroundColor: 'buttonPrimaryBg',
    },
    secondary: {
      backgroundColor: 'buttonSecondaryBg',
      borderColor: 'buttonSecondaryBorder',
      borderWidth: 1,
    },
    danger: {
      backgroundColor: 'buttonDangerBg',
    },
    defaults: {
      borderWidth: 1,
      borderColor: 'transparent',
    },
  },
});

export type Theme = typeof theme;
export default theme;
