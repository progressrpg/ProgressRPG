# Restyle PoC — cross-platform styling-layer alternative to Tamagui

Scope: following on from the Tamagui (#629) and Gluestack (#631) PoCs, this
spike checks `@shopify/restyle` as a lighter-weight cross-platform styling
alternative, once real native (not just `react-native-web`) was confirmed as
the actual driver behind the primitives/styling-layer exploration - which
rules out web-only options (SCSS, vanilla-extract, Panda, StyleX) as
permanent answers and narrows the field to systems that genuinely run on
iOS/Android. `@shopify/restyle` (last published 2026-04, actively
maintained) was picked over `dripsy` (last published 2024-10, ~21 months
stale) on maintenance signal alone, before writing any code.

Branch: `claude/restyle-poc`. Same methodology as the prior three PoCs: wire
the real toolchain, port the same two components (`OnlineCountBadge`
trivial case, `Button` hard case: variant + breakpoint), measure real
bundle deltas, run/attempt the existing test suites, confirm visual parity
via a real browser.

## What was done

- Installed `@shopify/restyle`, `react-native-web`.
- Built `restyle-theme.ts` (`createTheme()`) and `restyle-components.tsx`
  (`Box`/`Text`/`PressableBox` factories bound to that theme), hand-copied
  from this app's own SCSS tokens - same as the Tamagui PoC had to do,
  Restyle has no more visibility into the SCSS pipeline than Tamagui did.
- Wired `<ThemeProvider>` at the app root in `main.tsx`, `resolve.alias`
  (`react-native` → `react-native-web`) in `vite.config.ts` - same pattern
  all three prior PoCs needed.
- Ported `OnlineCountBadge.restyle.tsx` (trivial) and `Button.restyle.tsx`
  (hard case: `$text-button`'s `md` breakpoint + primary/secondary/danger
  variants).
- Measured real production bundle deltas, before/after, same methodology
  as the other three PoCs.
- Confirmed visual parity and breakpoint/interaction behavior via a real
  Playwright/Chromium build (not just inspection or unit tests) - required
  here, not optional, for the reason below.

## Toolchain findings

- **No JSX-packaging-bug workaround needed** - unlike all three prior PoCs
  (`@rn-primitives`, Gluestack/NativeWind, and indirectly Tamagui's own
  dependency chain), `@shopify/restyle`'s published output didn't need any
  esbuild-transform workaround to build. One fewer piece of toolchain
  fragility than the others.
- **Vitest cannot load `@shopify/restyle` at all - confirmed as the same
  wall the Gluestack PoC hit, not assumed.** `@shopify/restyle`'s compiled
  `dist/index.js` does a raw CJS `require('react-native')` at module-init
  time. Tried all three documented fixes, in order, each confirmed
  ineffective by actually running it: `server.deps.inline` (regex-matched
  against the package), `ssr.noExternal` (same), and `vi.mock('react-native',
  ...)` in the test file itself. All three produced the identical
  `SyntaxError: Unexpected token 'typeof'` (Flow syntax from the real
  `react-native` package's `index.js`), confirmed via `node -e
  "require('@shopify/restyle')"` outside Vitest entirely showing the same
  error with a clean stack trace: `Module.require` → `loadESMFromCJS`, not
  Vite's transform pipeline. This is the same class of dependency as
  Gluestack's `react-native-css-interop` - a real `react-native` package
  physically present in `node_modules` (pulled in as a peer/transitive
  dependency) with files doing raw `require("react-native")` that Node
  resolves directly, bypassing `resolve.alias` entirely. `OnlineCountBadge.
  restyle.test.tsx` and `Button.restyle.test.tsx` are excluded from the
  Vitest run in `vite.config.ts`, with this finding documented inline;
  verification for both ported components was done via a real Playwright
  browser build instead, same as the Gluestack PoC's methodology.
- **Full unit suite unaffected**: 346 pass / 12 pre-existing unrelated
  failures, identical to the baseline before this PoC (matching the
  documented baseline in the other three PoCs' findings docs exactly).
- **`npm run lint`**: same 4 pre-existing, unrelated issues as baseline
  (`ActivityRewardScreen.tsx`, `main.tsx`, `SuccessPage.tsx`,
  `vite.ds.config.js`) - nothing new from this PoC.

## Real bugs found while writing the code, not assumed from docs

- **Restyle's themed properties reject raw CSS literals - a real runtime
  crash, not a lint warning.** `borderColor: 'transparent'` (a completely
  standard value, needed for the button's default/no-border case) threw
  `Value 'transparent' does not exist in theme['colors']` at render time,
  confirmed via a Playwright `pageerror` before it was fixed. Unlike
  Tamagui (which accepts a literal value alongside token references in the
  same style object), Restyle's theme-keyed properties (`backgroundColor`,
  `borderColor`, `color`, ...) *only* accept values registered in the
  theme's own map - even placeholder/non-brand values like `transparent`
  need their own token entry. Fixed by adding a `transparent: 'transparent'`
  color token; left as a documented finding since it's a real ergonomic
  cost that recurs for every themed color prop, not a one-off.
- **`Pressable` renders with no ARIA role at all by default - not even
  `role="button"`.** Confirmed via real DOM inspection (not assumed): the
  initial port rendered a bare `<div tabindex="0">` with zero accessibility
  semantics - worse than Tamagui's `Button` (which does set `role="button"`
  automatically). Needed an explicit `accessibilityRole="button"` prop on
  every interactive component built on `Pressable`, confirmed to fix it.
  This is a real per-component tax any interactive Restyle component would
  need to remember to pay - nothing errors or warns if you forget it, the
  component just silently ships without accessibility semantics.
- **Once `accessibilityRole="button"` is set, `react-native-web` renders a
  real native `<button>` element, not a styled `<div>`** - confirmed via
  Playwright: `tagName` is `BUTTON`, and the `disabled` prop sets **both**
  the native HTML `disabled` attribute and `aria-disabled`, unlike
  Tamagui's `Button` (which only sets `aria-disabled`, a verified a11y gap
  in that PoC). This is a genuine, verified a11y win for Restyle over
  Tamagui on this specific point, once the role omission above is fixed.

## Interaction/behavior verification (real Chromium via Playwright, not unit tests)

Since Vitest is fully blocked for this library, every behavioral claim below
was checked in a real browser, not asserted from reading the API:

| Check | Result |
|---|---|
| Primary/secondary/danger variant background colors | **PASS** - exact `rgb()` match to the theme tokens |
| Keyboard activation (focus + `Enter`) fires `onClick` | **PASS** |
| Disabled button blocks click (even with a forced click) | **PASS** - native `disabled` attribute does the work |
| `$text-button`'s `md` breakpoint (16px → 18px at 768px width) | **PASS** - confirmed at both 500px and 900px viewports after a real resize, not just initial render |
| Visual parity (color, shape, rounding) vs. the SCSS original | **PASS** - screenshot-confirmed, matches Tamagui's PoC's own parity screenshot closely |

## Bundle cost

Production build, `index` chunk, before vs. after (provider + both
components), measured two independent ways that agreed within noise:

1. Real app build: 467.45 kB → 748.58 kB raw (144.93 kB → 231.27 kB gzip).
2. Standalone harness (React-only baseline vs. `ThemeProvider` + both
   components, isolated from the rest of the app): 190.38 kB → 473.73 kB
   raw (59.96 kB → 146.74 kB gzip) - same delta within a few hundred bytes.

**+281 kB raw / +86 kB gzip.** For comparison: smaller than Tamagui's
+506 kB/+144 kB (3 components), but nowhere near `@rn-primitives`' one-time
cost of +84 kB/+29 kB (which only covers primitives, not a styling system -
not a like-for-like comparison, since Restyle and `@rn-primitives` solve
different problems). The bulk of this is `react-native-web`'s runtime cost,
paid once regardless of how many components use it - consistent with every
prior PoC's finding on this point.

## Recommendation

`@shopify/restyle` is a credible, real alternative to Tamagui if the goal is
specifically a cross-platform styling system (not primitives - Restyle has
no overlay/interaction primitives at all, it only styles) with a **much**
smaller API surface and no compiler:

- **In its favor vs. Tamagui**: no separate build-time compiler to wire up
  or debug (no `.tamagui` cache, no extraction-timing surprises like the
  `$mdUp` false-negative that PoC needed real debugging to disprove); no
  confirmed upstream a11y bug like Tamagui's Tooltip (#4152) - though
  Restyle has no Tooltip/Popover primitives to compare directly, so this
  isn't a fully like-for-like claim; better default `disabled` semantics
  once `accessibilityRole` is set correctly (native `disabled` attribute,
  not just `aria-disabled`); smaller bundle cost (+281 kB vs. Tamagui's
  +506 kB for one more component).
- **Against it**: same Vitest-blocking wall as Gluestack - any component
  built on Restyle needs Playwright-based verification instead of unit
  tests, a real ongoing cost to the team's testing workflow, not a one-time
  PoC inconvenience; the theme-only-accepts-registered-tokens constraint is
  a real ergonomic tax (every raw literal, even `transparent`, needs its
  own token); the missing-ARIA-role-by-default gap on `Pressable` is a
  silent, easy-to-forget a11y footgun with no warning when omitted, which
  argues for wrapping every interactive primitive in an app-owned component
  from day one (a real but modest amount of scaffolding work).

**Net**: Restyle is the strongest cross-platform styling contender found so
far *if native is genuinely the goal and Vitest coverage for styled
components is an acceptable trade for real-browser verification* - it's
smaller, simpler, and free of Tamagui's confirmed Tooltip bug. But "no unit
tests, ever, for anything built on this library" is a real, ongoing cost to
weigh against Tamagui's heavier-but-more-fully-unit-testable footprint (only
Tooltip was blocked in the Tamagui PoC; Button and OnlineCountBadge both had
real, passing Vitest coverage there). Given `@rn-primitives` is the
separately-recommended choice for primitives (#579), and neither Restyle
nor Tamagui is required to make that decision, my read is: prototype the
actual design tokens in whichever system is chosen last, since token
definition work (not the styling API) is the larger, harder-to-avoid cost
either way - and treat "does it survive contact with Vitest" as a
first-class selection criterion going forward, since it has now decided the
outcome for two of the four systems evaluated (Gluestack, Restyle) before
any other factor mattered.

## Files changed on this branch

`src/restyle-theme.ts` (new), `src/restyle-components.tsx` (new),
`src/components/OnlineCountBadge/OnlineCountBadge.restyle.tsx` (new) +
`.test.tsx` (new, excluded from Vitest run),
`src/components/Button/Button.restyle.tsx` (new) + `.test.tsx` (new,
excluded from Vitest run), `src/main.tsx`, `vite.config.ts`,
`package.json`/`package-lock.json`.
