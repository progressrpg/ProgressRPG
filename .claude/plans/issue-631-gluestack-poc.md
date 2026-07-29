# Issue #631 — Gluestack UI PoC (combined primitives + styling choice)

Scope: companion spike to #629 (Tamagui), per that issue's own acceptance
criteria and conclusion — still warranted because Gluestack is
architecturally the opposite bet: NativeWind/Tailwind atomic-CSS styling
instead of a compiled runtime engine, and `@react-native-aria` for
accessibility instead of Tamagui's from-scratch Popper/floating-ui
implementation. Same shape as #629 and #579's PoCs, for direct
comparability: same two components (`OnlineCountBadge`, `Button`), same
primitive swap target (`Tooltip`), same bundle-delta methodology.

## What was done

- Installed `nativewind`, `tailwindcss@^3`, `postcss`, `autoprefixer`,
  `@gluestack-ui/button`, `@gluestack-ui/tooltip`, `@gluestack-ui/overlay`,
  `@gluestack-ui/nativewind-utils`, `tailwind-variants`,
  `class-variance-authority`, `@react-native-aria/interactions`,
  `@react-native-aria/focus`, `react-native-web`.
- Wired Tailwind (`tailwind.config.js` + `postcss.config.js`) and a
  `src/styles/tailwind.css` entry with the standard `@tailwind` directives.
- Ported the same two components #629 ported:
  - **Trivial:** `OnlineCountBadge` → `OnlineCountBadge.gluestack.tsx`
  - **Hard case** (`apply-text-style` + a variant mixin + a breakpoint):
    `Button` → `Button.gluestack.tsx`
- Swapped `Tooltip`'s primitive → `Tooltip.gluestack.tsx`, using
  `@gluestack-ui/tooltip` (built on `@react-native-aria`, not Radix and not
  a from-scratch reimplementation like Tamagui's).
- Verified all of the above in a real Chromium browser against a real
  production-mode Vite build (Playwright), including a visual-parity
  screenshot and a two-viewport breakpoint check — the same methodology
  #629 used for its own verification.
- Attempted the same Vitest-based approach #579/#629 used for the Tooltip
  test suite; this **did not work** for Gluestack (see below), and that
  failure is itself one of this PoC's most important findings.

## The core architectural finding: NativeWind's styling is not optional or scoped

Initial assumption, based on `nativewind` exporting a `cssInterop()`
function callable per-component: that Gluestack/NativeWind styling could be
wired in *scoped*, the way `@rn-primitives` (#579) and Tamagui's imports
(#629) only affect files that opt in — avoiding Tamagui's cost of a
mandatory app-wide `<TamaguiProvider>`. **This is wrong**, verified by
actually building it both ways:

- `cssInterop(Component, { className: 'style' })` only *registers* that a
  prop name should be treated as a style source. The actual `className` ->
  RN-style-object conversion happens inside NativeWind's custom JSX pragma
  (`react-native-css-interop`'s `jsx`/`jsxs` wrapper functions) - which only
  runs when Vite's `jsxImportSource` points at `nativewind` for the file
  being compiled.
- With `react()` (default JSX runtime) and `cssInterop()` called: a
  Gluestack `Button`'s Tailwind classes produced **no styling at all** -
  `getComputedStyle` showed a transparent background, zero padding, no
  border-radius. Not a bug in this PoC's code; verified as the actual
  behavior of the mechanism.
- Switching to `react({ jsxImportSource: 'nativewind' })` fixed that one
  component immediately - background, padding, border-radius, and the
  breakpoint font-size all matched.
- **But `jsxImportSource` is a compiler-wide setting, not scoped to files
  that import Gluestack.** Turning it on breaks **all 41 of this app's
  pre-existing unit test files**, not just the 3 new Gluestack ones -
  confirmed by actually flipping the switch and running the full suite
  (`354 passed` -> effectively all suites failing with `SyntaxError:
  Unexpected token 'typeof'`, the exact same failure documented below for
  the Gluestack tests specifically, just now hitting *every* JSX-emitting
  file in the app). The reason: every file now imports
  `nativewind/jsx-runtime` -> `react-native-css-interop`, which requires
  `react-native` at module-init time - and that hits the CJS wall described
  next, for literally every component.

There is no working middle ground found in this toolchain: it's "every
existing test breaks" or "Gluestack renders unstyled." The shipped state on
this branch uses the *safe* option (plain `react()`, existing 346 tests
still pass, 12 pre-existing unrelated failures unchanged) - the
`jsxImportSource: 'nativewind'` alternative was only switched on long
enough to take the measurements in this document, then reverted. See
`vite.config.ts` for the in-place comment recording both states.

## Bundle size, measured both ways

All numbers are the `index` chunk (+ the new `jsx-runtime` shared chunk,
where relevant - both load on initial page view so they're summed), `npm
run build:production`.

| Stage | Raw | Gzip |
|---|---|---|
| Baseline (`development`, no Gluestack) | 467.19 kB | 144.88 kB |
| Safe config (`react()`, Tailwind CSS wired, zero components styled) | 467.45 kB | 144.93 kB |
| **Working config** (`jsxImportSource: 'nativewind'`), zero components used | 752.91 kB (285.31 + 467.60) | 233.61 kB (88.21 + 145.40) |
| **Working config**, all 3 components mounted | 804.05 kB (336.23 + 467.82) | 250.78 kB (105.27 + 145.51) |

Two things worth separating:

1. **The "safe config" row is nearly free** (+0.26 kB raw / +0.05 kB gzip)
   - but it's also non-functional for anything using Gluestack, so it's not
   a fair comparison point on its own.
2. **The real, working-config cost** (+336.86 kB raw / +105.90 kB gzip for
   wiring + all 3 components) is meaningfully **lighter than Tamagui's
   equivalent total** (#629: +505.8 kB raw / +144.4 kB gzip for provider +
   3 components) - Gluestack does come out ahead on bundle size once both
   are made to actually work, it's just not the "near-zero, opt-in" story
   the scoped `cssInterop()` approach first suggested.

## Component ports: what worked, what didn't

### `OnlineCountBadge` (trivial)

Ports cleanly onto a `cssInterop`'d `View` with Tailwind arbitrary-value
classes (`bg-white`, `border-[#007a32]`, etc.) once the JSX-runtime
requirement above is satisfied. Same token-provenance caveat as #629:
values are hand-copied from the SCSS tokens' resolved output, since
Tailwind's default theme has no visibility into this app's own scale (#590
would need to feed a real `tailwind.config.js` theme, not arbitrary-value
classes like this PoC uses).

### `Button` (hard case) - variants and breakpoint both verified working

- **Real API-shape bug found and fixed**: `@gluestack-ui/button`'s exported
  `createButton()` takes an *object* — `{ Root, Text, Group, Spinner, Icon }`
  — not a single styled component. Reading only the inner factory
  function's signature (`(StyledButton) => ...`) in `Button.tsx` suggests
  the latter; that's not the actual public `createButton()` export in
  `index.tsx`. Passing a single component directly produces `Root:
  undefined`, silently, with no error until render (`Element type is
  invalid... got: undefined`). A real, verified footgun, not a hypothetical
  one - caught only by tracing the actual render error back through
  `index.tsx`.
- **Variant + breakpoint styling both verified correct against a real
  browser, at the computed-style level**: background `#007a32`
  (primary)/`#e7fff1` (secondary)/`#c62828` (danger) all matched; the `md:`
  breakpoint (`apply-text-style`'s `$text-button` `md` layer) produced
  `16px` at a 500px viewport and `18px` at 900px - **this is the one place
  Gluestack does noticeably better than Tamagui's PoC**, whose equivalent
  breakpoint didn't apply at all. The reason: Tailwind's *default* `md`
  breakpoint (768px) already matches this app's own SCSS breakpoint
  (`src/styles/base/_variables.scss`) exactly - no custom `theme.screens`
  override was needed, unlike Tamagui's stock preset (`md: 1020`).
- State-based variants (hover/press) use `@gluestack-ui/nativewind-utils`'s
  `tva` + `withStates`, which resolve `data-[hover=true]:bg-...`-shaped
  class tokens **in JavaScript against the state object `createButton`'s
  HOC provides** - not via real CSS attribute selectors. Worth noting as a
  real difference from how it reads on paper (looks like a CSS
  attribute-selector convention; is actually resolved in JS at render time).
- Naming collision, smaller than Tamagui's but real: `createButton`'s
  factory result is generically named (no reserved `variant` prop the way
  Tamagui's `Button` has), so no rename was needed here - a genuine, if
  minor, point in Gluestack's favor for this specific case.

### `Tooltip` (primitive swap) - functionally closer to Radix than either prior PoC, with two real gaps

`@gluestack-ui/tooltip`'s `Tooltip` root wires hover open/close, focus
open/close, and Escape-to-close (via `@react-native-aria/interactions`'
`useKeyboardDismissable`) **without any extra opt-in flag** - a real
advantage over Tamagui's PoC, which needed `focus={{ enabled: true }}` and
still failed the focus/Escape cases. Verified against a real browser
(Playwright, real `hover()`/`focus()`/`Escape` interactions, not just
`onOpen`/`onClose` callbacks):

| Interaction | Result |
|---|---|
| Hover opens the tooltip | **PASS** |
| Hover-out closes it | **PASS** |
| Focus opens the tooltip, `aria-describedby` resolves to the tooltip's own id | **PASS** |
| Escape dismisses it | **FAIL** |
| Clicking elsewhere closes it (via blur) | PASS (bonus - not in the original 3-case suite) |

Two real, verified gaps behind that mostly-green result:

1. **Nothing renders at all without an undocumented `<OverlayProvider>`
   wrapper.** `onOpen`/`onClose` fire correctly and the trigger's
   `aria-describedby` gets set even with zero tooltip content ever reaching
   the DOM - confirmed by diagnosing this exact "looks like it's working,
   isn't" case directly: the component fails *silently*, no console error,
   until `<OverlayProvider>` (re-exported by `@gluestack-ui/overlay` from
   `@react-native-aria/overlays`) is mounted somewhere above it in the tree
   - the same shape of requirement as Tamagui's `<TamaguiProvider>` or this
   app's own `<TooltipProvider>`, just entirely absent from
   `@gluestack-ui/tooltip`'s own type signature or README.
2. **Escape-to-close does not work**, confirmed with `<OverlayProvider>`
   correctly mounted (ruling out gap #1 as the cause) - `useKeyboardDismissable`
   is wired internally per the source, but pressing Escape in a real browser
   left the tooltip open. Root cause not fully diagnosed within this
   PoC's timebox; recorded as a verified failure, not assumed to work
   because the library "should" handle it.
3. **Positioning is broken on web**: `@react-native-aria/overlays`' position
   calculation throws `ref.current.measureInWindow is not a function` (a
   real, uncaught console error) - `measureInWindow` is a React Native
   *native* `View` method that `react-native-web`'s `View` doesn't
   implement. The tooltip still opens/closes correctly and gets the right
   ARIA wiring, but renders off-screen (`top: -1000px; left: -1000px`) - a
   real, verified visual/functional gap for actual on-screen use, distinct
   from the Escape-key gap above.
4. **Duplicate `role="tooltip"`**: both the outer overlay wrapper and the
   inner content node get `role="tooltip"` - inherent to the library's own
   DOM structure (confirmed by not setting `role` anywhere in this PoC's
   own styled components), not a mistake specific to this port. Same class
   of finding as #629's Tamagui PoC hit (there, self-inflicted and fixed;
   here, upstream and unfixed).

### Vitest could not run any of this - a decisive, separate finding

Unlike #579's `@rn-primitives` PoC (fixed with `server.deps.inline` +
`resolve.alias`) and #629's Tamagui PoC (same technique, also worked), the
same fix does **not** work for Gluestack/NativeWind. Root cause, confirmed
via a stack trace: several of NativeWind's and `@react-native-aria`'s
dependencies (`react-native-css-interop`'s runtime, nested
`@react-native-aria/overlays` copies) do a raw CJS `require("react-native")`
inside already-compiled output. Once Node's native CJS loader takes over
for a `require()` call (as opposed to an ESM `import`), it resolves against
the real, physically-installed `react-native@0.86.2` package (pulled in
transitively by `@gluestack-ui/button`/`@react-native-aria/*` as an actual
dependency, not just a type declaration) - and that package's own
Flow-typed source can't be parsed by anything in this toolchain. Tried and
confirmed ineffective: `resolve.alias`, `ssr.noExternal`, `test.server.deps.inline`,
and `vi.mock('react-native', ...)` - none of them reach a plain Node
`Module.require()` call once execution has left Vite's own module graph.
`OnlineCountBadge.gluestack.test.tsx` is committed as a demonstration of
this exact failure and excluded from the default Vitest run (see
`vite.config.ts`) rather than left to fail the suite. All verification for
the Gluestack-ported components in this PoC was done via a real Chromium
browser against a production build instead (Playwright) - a materially
different, and more expensive to set up, verification path than either
prior PoC needed.

## Toolchain friction, beyond the two big findings above

- Installing the Gluestack/`@react-native-aria` dependency tree twice
  bumped `react`/`react-dom` out of lockstep (`react@19.2.8` vs
  `react-dom@19.2.0`), the same npm quirk #629 hit - except here it was
  forced further, to `19.2.8` for both, because `react-native@0.86.2`'s own
  peer dependency (`^19.2.3`) is stricter than this app's `^19.2.0`. A real,
  if small, version-floor cost of pulling in `@react-native-aria/*`.
- The same "published raw, un-transpiled JSX" packaging bug #579 found in
  `@rn-primitives` recurs here too, in `react-native-css-interop/dist/doctor.js`
  and other files across `nativewind`/`@gluestack-ui`/`@react-native-aria` -
  needed the identical scoped esbuild-transform workaround.
- Font family did not carry over: the original `Button`'s SCSS token
  specifies `Roboto, sans-serif` explicitly; Tailwind's default `font-sans`
  utility resolves to a generic system-font stack, not `Roboto` - visible
  in the parity screenshot as a subtle font-rendering difference. Same
  "needs a real `tailwind.config.js` theme, not defaults" gap noted above
  for colors/spacing.

## Visual parity

Confirmed by rendering both `Button` versions (all three variants) side by
side via a throwaway Vite build + Playwright screenshot, same methodology
#629 used. Colors and shape match closely - arguably closer to the
original's fully-pill border-radius than Tamagui's port was - with the
font-family gap noted above as the one visible difference.

## Recommendation

**Gluestack does not supersede #579's `@rn-primitives` recommendation
either**, but it beats Tamagui (#629) on several concrete points while
losing decisively on one:

- **Wins over Tamagui**: lighter total bundle cost once both are made to
  actually work (+336.86 kB/+105.90 kB gzip vs. Tamagui's +505.8 kB/+144.4 kB
  gzip); the breakpoint case that broke for Tamagui works correctly here,
  verified at the computed-style level; Tooltip's focus-to-open and
  hover-to-close both work out of the box, unlike Tamagui's PoC.
- **Loses decisively to both #579 and #629**: NativeWind's core styling
  mechanism cannot be scoped to just the files that use it - the
  `jsxImportSource` swap needed to make any of this functional breaks the
  *entire* existing unit test suite (41 files), not just the 3 ported
  components. That is a materially worse adoption cost than either prior
  PoC found, and it isn't a corner that can be config'd away within this
  toolchain as verified here. Layered on top: Tooltip needs an undocumented
  `<OverlayProvider>` to render at all, Escape-to-close doesn't work, and
  on-screen positioning is broken by a react-native-web incompatibility
  (`measureInWindow`).

**For #578/#591**: this doesn't change #629's conclusion - stay with
#579's `@rn-primitives` recommendation for primitives, and keep #591's
styling-layer decision unblocked by either UI-kit's bundled token/variant
system. Between the two kits tested, if a broader kit were ever
reconsidered, Gluestack's bundle profile and breakpoint behavior are the
stronger half of the story - but its test-suite-breaking JSX-runtime
requirement and unresolved Tooltip gaps (positioning, Escape) are, on their
own, disqualifying for adoption as verified in this PoC's timebox.

## Files changed on this branch

`tailwind.config.js` (new), `postcss.config.js` (new),
`src/styles/tailwind.css` (new), `vite.config.ts`, `src/main.tsx` (Tailwind
CSS import), `src/components/OnlineCountBadge/OnlineCountBadge.gluestack.tsx`
(+ test, excluded from the default Vitest run - see above),
`src/components/Button/Button.gluestack.tsx`,
`src/components/Tooltip/Tooltip.gluestack.tsx`, `package.json`/
`package-lock.json` (new dependencies). The three `.gluestack` PoC
components are standalone files, not wired into the live app - same
posture #579's and #629's PoCs both took.
