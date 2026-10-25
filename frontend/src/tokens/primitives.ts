// Primitive design tokens - the platform-neutral source of truth (#592).
//
// scripts/generate-tokens.ts turns this file (plus semantic.ts) into the
// Sass partials under src/styles/tokens/, src/styles/base/_variables.scss
// and src/styles/semantic/, and into resolved.generated.ts for runtime
// consumers (tamagui.config.ts, and later native). Edit here, then run
// `npm run tokens:generate`; never edit the generated files directly.
//
// Lengths are unitless px numbers (rem / px / ms units are added by the
// generator for Sass), so the same values work on native.

// A colour is either a literal CSS colour string or a recipe derived from
// another colour. Recipes are resolved by the `sass` package inside the
// generator - the same engine that compiled them before #592 - so the
// derived values match the previous Sass output exactly.
export type ColorValue = string | ColorAdjust | ColorAlpha;

export interface ColorAdjust {
  kind: 'adjust';
  base: ColorValue;
  /** Percentage points, as Sass `color.adjust($lightness: ...)`. */
  lightness: number;
}

export interface ColorAlpha {
  kind: 'alpha';
  base: ColorValue;
  alpha: number;
}

export const adjust = (base: ColorValue, lightness: number): ColorAdjust => ({
  kind: 'adjust',
  base,
  lightness,
});

export const alpha = (base: ColorValue, value: number): ColorAlpha => ({
  kind: 'alpha',
  base,
  alpha: value,
});

// === Colours ===

export const color = {
  primary: '#007a32',
  secondary: '#e7fff1',
  light: '#fefefe',
  dark: '#2c3e50',
  accent: '#ff8800',
  border: 'rgba(0, 0, 0, 0.15)',
};

// Colour scales. Sass access: map.get($primary-scale, 300).
export const scale = {
  primary: {
    '050': adjust(color.primary, 40),
    '100': adjust(color.primary, 30),
    '200': adjust(color.primary, 20),
    '300': adjust(color.primary, 10),
    // Capped at +2.5% (not the +5%/+10%/... step used elsewhere in this scale)
    // because primary-scale 400 backs white-on-primary text (button hover,
    // selected-list-item hover) - +5% drops below the 4.5:1 WCAG AA contrast
    // ratio required for that text (#00943c ~3.93:1 vs #fefefe).
    '400': adjust(color.primary, 2.5),
    '500': color.primary,
    '600': adjust(color.primary, -5),
    '700': adjust(color.primary, -10),
    '800': adjust(color.primary, -15),
    '900': adjust(color.primary, -20),
  },
  secondary: {
    // Out of gamut: resolves to hsl(145, 100%, 105.29%), which browsers clamp
    // to white. Kept as-is for output parity - see #857.
    '050': adjust(color.secondary, 10),
    '100': color.secondary,
    '200': adjust(color.secondary, -5),
    '300': adjust(color.secondary, -10),
    '400': adjust(color.secondary, -15),
    '500': adjust(color.secondary, -20),
  },
  accent: {
    '050': adjust(color.accent, 20),
    '100': adjust(color.accent, 10),
    '200': color.accent,
    '300': adjust(color.accent, -10),
    '400': adjust(color.accent, -15),
    '500': adjust(color.accent, -20),
  },
  light: {
    '050': '#ffffff',
    '100': adjust(color.light, -3),
    '200': adjust(color.light, -6),
    '300': adjust(color.light, -9),
    '400': adjust(color.light, -12),
  },
  neutral: {
    '000': '#ffffff',
    '100': '#f5f5f5',
    '200': '#e0e0e0',
    '300': '#c2c2c2',
    '400': '#9e9e9e',
    '500': '#707070',
    '600': '#4d4d4d',
    '700': '#2c2c2c',
    '800': '#1a1a1a',
    '900': '#0a0a0a',
  },
  dark: {
    '50': adjust(color.dark, 20),
    '100': adjust(color.dark, 10),
    '200': color.dark,
    '300': adjust(color.dark, -10),
    '400': adjust(color.dark, -20),
    '500': adjust(color.dark, -30),
  },
};

// === Spacing (px) ===
// The single spacing scale. semantic.ts composes it into higher-level tokens
// (gap, padding, radius); don't redefine the scale anywhere else. (`md-lg`
// was dropped in #590 - it had no consumer.)
export const spacing = {
  xs: 4,
  sm: 8,
  md: 16,
  lg: 32,
  xl: 64,
  '2xl': 96,
  '3xl': 128,
};

// === Typography ===
export const typography = {
  fontFamily: {
    base: ['Roboto', 'sans-serif'],
    heading: ['Roboto', 'sans-serif'],
  },
  // px
  fontSize: {
    '2xs': 10,
    xs: 12,
    sm: 14,
    md: 16,
    base: 16,
    lg: 20,
    xl: 24,
    '2xl': 32,
    '3xl': 40,
    '4xl': 48,
  },
  fontWeight: {
    light: 300,
    regular: 400,
    medium: 500,
    bold: 600,
    extrabold: 700,
  },
  lineHeight: {
    tight: 1.2,
    snug: 1.35,
    base: 1.5,
    relaxed: 1.625,
    loose: 1.75,
  },
  // em
  letterSpacing: {
    tighter: -0.05,
    tight: -0.025,
    normal: 0,
    wide: 0.025,
    wider: 0.05,
  },
  textTransform: {
    uppercase: 'uppercase',
    none: 'none',
    capitalize: 'capitalize',
  },
  textDecoration: {
    none: 'none',
    underline: 'underline',
    lineThrough: 'line-through',
  },
  textAlign: {
    left: 'left',
    center: 'center',
    right: 'right',
    justify: 'justify',
  },
};

// === Layout & motion ===
// Breakpoints drive respond-to() (and Tamagui's `media`), z-index establishes
// the stacking order across components, and durations/easing drive
// transitions.

// px
export const breakpoints = {
  sm: 576,
  md: 768,
  lg: 992,
  xl: 1200,
  xxl: 1440,
};

export const zIndex = {
  base: 1,
  dropdown: 10,
  header: 50,
  modal: 100,
  toast: 200,
  tooltip: 300,
  overlay: 999,
};

// ms
export const duration = {
  fast: 150,
  base: 250,
  slow: 400,
};

export const easing = {
  standard: 'ease-in-out',
};
