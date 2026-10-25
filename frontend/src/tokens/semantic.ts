// Semantic design tokens - composed from primitives.ts (#592).
//
// Generated into src/styles/semantic/_colors.tokens.scss and
// src/styles/semantic/_spacing.scss (camelCase keys become kebab-case Sass
// names: colorTextBody -> $color-text-body). Edit here, then run
// `npm run tokens:generate`.
import { adjust, alpha, color, scale, spacing } from './primitives.ts';

const { primary, secondary, accent, neutral } = scale;

const danger = '#c62828'; // strong, readable red

// === Colours ===
export const semanticColor = {
  colorTextPrimary: '#1e1e1e',
  colorTextInvert: '#fbfbfb',

  colorDisabled: neutral['500'],
  colorLightHover: adjust(color.light, -5),
  colorDarkHover: adjust(color.dark, 5),

  // Text
  colorTextBody: neutral['700'],
  colorTextHeading: neutral['900'],

  // Buttons
  buttonBgPrim: primary['500'],
  buttonBgPrimHov: primary['600'],

  colorProgressBar: primary['500'],

  // Backgrounds
  colorBg: secondary['050'],
  colorBgGreen: secondary['100'],
  colorBgInvert: color.dark,

  // Borders
  colorBorderPrimary: primary['500'],
  colorBorderAccent: accent['200'],
  colorGlowingOutline: primary['500'],

  // Status
  colorStatusInfo: primary['500'],
  colorStatusSuccess: primary['600'],
  colorStatusWarning: accent['200'],
  colorDanger: danger,
  colorStatusDanger: danger,

  // Activity categories
  colorPlayer: primary['500'],
  colorCharacter: accent['200'],

  // Error/Warning states
  colorError: danger,
  colorErrorBg: '#ffebee',
  colorWarning: '#ff9800',
  colorWarningDark: '#f57c00',

  // Text colors
  colorTextError: danger,
  colorTextDisabled: neutral['400'],
  colorTextMuted: neutral['500'],
  // colorTextMuted (neutral 500, #707070) only clears 4.5:1 against ~white
  // backgrounds (4.95:1). Tinted surfaces like .tonePlayer's rgba($color-player,
  // 0.08) darken the background enough to drop it to 3.64:1 - use this instead
  // wherever muted text sits on a tinted list-item background.
  colorTextMutedStrong: neutral['600'],
  colorTextDefault: neutral['900'],

  // Border colors
  colorBorderDefault: neutral['300'],
  colorBorderLight: neutral['200'],
  colorBorderHover: primary['400'],
  colorBorderFocus: accent['200'],
  colorBorderError: danger,

  // Overlay colors
  colorOverlayBackdrop: 'rgba(0, 0, 0, 0.5)',
  colorOverlayLight: 'rgba(0, 0, 0, 0.4)',

  // Third-party brand colors
  colorBrandGithub: '#24292e',
  colorBrandGoogle: '#34a853',
  colorBrandDiscord: '#5865f2',
};

export const textTone = {
  default: { color: neutral['900'] },
  heading: { color: neutral['800'] },
  muted: { color: neutral['500'] },
  inverted: { color: color.light },
  primary: { color: primary['600'] },
  secondary: { color: secondary['100'] },
  accent: { color: accent['200'] },
  error: { color: danger },
  disabled: { color: neutral['400'] },
};

export const buttonVariants = {
  primary: {
    tone: 'inverted',
    bg: primary['500'],
    hover: primary['400'],
    active: primary['600'],
    disabled: neutral['800'],
  },
  secondary: {
    tone: 'primary',
    bg: secondary['100'],
    hover: secondary['200'],
    active: secondary['300'],
    disabled: neutral['100'],
  },
  accent: {
    tone: 'accent',
    bg: accent['200'],
    hover: accent['300'],
    active: accent['400'],
    disabled: accent['100'],
  },
  danger: {
    tone: 'inverted',
    bg: danger,
    hover: '#b71c1c',
    active: '#8e0000',
    disabled: alpha(danger, 0.4),
  },
};

// `default.tone: 'base'` names a tone $text-tone doesn't have, so the Sass
// lookup returns null, and the `hover` keys are unused while
// apply-list-variant's hover block is commented out. Both are preserved
// as-is for output parity; #594 owns resolving them.
export const listVariants = {
  default: {
    tone: 'base',
    selectedTone: 'inverted',
    bg: 'transparent',
    hover: neutral['100'],
    active: neutral['200'],
    selected: primary['500'],
    selectedHover: primary['400'],
    selectedActive: primary['600'],
  },
  subtle: {
    tone: 'secondary',
    bg: 'transparent',
    hover: secondary['100'],
    active: secondary['200'],
    selected: accent['100'],
    selectedHover: accent['200'],
    selectedActive: accent['300'],
  },
};

// === Spacing (px) ===
// Composes the single spacing scale into the semantically-named values used
// across the app. Array values are shorthand pairs (vertical horizontal).
const paddingVertical = spacing.sm;
const paddingHorizontal = spacing.md;
const borderRadius = spacing.sm;

export const semanticSpacing = {
  // Flat scalars
  spacingXs: spacing.xs,
  spacingSm: spacing.sm,
  spacingMd: spacing.md,
  spacingLg: spacing.lg,
  spacingXl: spacing.xl,
  spacing2xl: spacing['2xl'],
  spacing3xl: spacing['3xl'],

  spacingGap: spacing.sm,

  // Padding shorthands
  paddingVertical,
  paddingHorizontal,

  paddingSm: [spacing.xs, spacing.sm],
  paddingBase: [paddingVertical, paddingHorizontal],
  paddingLg: [spacing.md, spacing.lg],

  // Component shortcuts
  borderRadius,
  buttonPadding: [spacing.xs, spacing.md],
  buttonRadius: spacing.md,
  contentPadding: spacing.lg,

  formControlHeight: 32,
  formControlRadius: borderRadius,

  // Gap / radius / shadow collections
  gap: {
    xs: spacing.xs,
    sm: spacing.sm,
    md: spacing.md,
    lg: spacing.lg,
  },

  paddingVerticalSm: spacing.sm,
  paddingHorizontalSm: spacing.md,

  spacingPadding: {
    base: [spacing.sm, spacing.md],
  },

  cardPadding: [spacing.sm, spacing.md],

  radius: {
    sm: spacing.xs,
    md: spacing.sm,
    lg: spacing.md,
  },

  // Box-shadow strings stay CSS until #597 ports shadows to native.
  shadow: {
    sm: '0 1px 2px rgba(0, 0, 0, 0.1)',
    md: '0 4px 8px rgba(0, 0, 0, 0.1)',
    lg: '0 8px 16px rgba(0, 0, 0, 0.1)',
  },
};
