# Issue #629 — Tamagui PoC (combined primitives + styling choice)

Scope: PoC-verify Tamagui as the combined primitives-and-styling answer for
#578/#591, per #579's own note that a kit choice there "likely decides this
too." Companion to `.claude/plans/issue-579-rn-primitives-library-exploration.md`
(the `@rn-primitives` PoC on branch `claude/rn-primitives-library-4ny4sa`) -
same Tooltip swap, run against the same test suite, for a direct comparison.

## What was done

- Installed `tamagui`, `@tamagui/core`, `@tamagui/config`,
  `@tamagui/vite-plugin`, `react-native-web`.
- Wired `@tamagui/vite-plugin`'s compiler into `vite.config.ts` and confirmed
  it's actually active during both `vite build` and `vitest` (not just
  installed) - the build log shows a `tamagui-extract` plugin timing entry,
  and `tamagui.config.ts`'s `createTamagui(...)` output is inspectable in
  the bundled output.
- Added `tamagui.config.ts` (based on `@tamagui/config`'s default web
  preset) and mounted `<TamaguiProvider>` at the app root in `main.tsx`.
- Ported two components, per the PoC scope:
  - **Trivial (styling only):** `OnlineCountBadge` →
    `OnlineCountBadge.tamagui.tsx`
  - **Hard case** (`apply-text-style` + a variant mixin + a breakpoint):
    `Button` → `Button.tamagui.tsx`, exercising `$text-button`'s `md`
    breakpoint layer and `apply-button-variant`'s primary/secondary/danger
    variants.
- Swapped the underlying primitive on `Tooltip` → `Tooltip.tamagui.tsx`,
  using Tamagui's own `Tooltip` (built on `@tamagui/popper`/floating-ui, not
  Radix) - the same component #579's `@rn-primitives/tooltip` PoC swapped,
  for an apples-to-apples comparison.
- Ran this branch's actual `Tooltip.test.tsx` suite (3 cases: hover
  show/hide, focus + `aria-describedby`, Escape-to-close) against the
  Tamagui swap. Note: this branch predates #568's click/tap-to-toggle
  rework merging into `development`, so it's the 3-case hover-based suite
  actually present here, not the 5-case one #579's PoC branch had (that
  branch's history includes #568). Comparison below is on the primitive
  swap mechanics, not the exact case count.
- Measured real production bundle deltas (raw + gzip, `index` chunk),
  before/after, same methodology as #579.
- Confirmed visual parity for `Button` via an actual rendered screenshot
  (Playwright, both versions side by side) - see below.

## Bundle size, verified in three stages

All numbers are the `index` chunk, `npm run build:production`.

| Stage | Raw | Gzip |
|---|---|---|
| Baseline (`development`, no Tamagui) | 467.19 kB | 144.88 kB |
| + Tamagui compiler wired, `<TamaguiProvider>` mounted, **zero components ported** | 850.55 kB | 247.35 kB |
| + both ported components mounted for real (temporary, reverted after measuring) | 972.99 kB | 289.28 kB |

**The single biggest number here is the middle row: +383 kB raw / +102 kB
gzip before a single component is touched.** That's `react-native-web`'s
runtime (View/Pressable/StyleSheet shims - same cost #579 found) plus
Tamagui's own core/compiler runtime and `@tamagui/config`'s stock preset
(fonts, full color scale, animations, media driver), none of which is
optional - it's the fixed cost of turning the provider on at all.

Against that fixed cost, the two ported components + the Tooltip primitive
swap add relatively little more: +122 kB raw / +42 kB gzip for all three
combined. That matches #579's finding that *later* primitives cost much
less than the first once the runtime is paid for - but Tamagui's fixed
runtime floor (+383/+102) is roughly **4.5x `@rn-primitives`' equivalent
floor** (+84 kB raw / +29 kB gzip for `@rn-primitives/tooltip` + `portal`),
because Tamagui ships a full compiled-styling engine and design-token system
on top of the same `react-native-web` cost, not just unstyled primitives.

(Numbers for the "+ both components mounted" row were taken by temporarily
importing and rendering `OnlineCountBadge.tamagui`, `Button.tamagui`, and
`Tooltip.tamagui` from `AppContent.tsx`, to force real bundler inclusion
rather than measuring dead-code-eliminated unused exports; that mount was
reverted before this branch's final state - the three components are PoC
files, not wired into the live app.)

## Component ports: what worked, what didn't

### `OnlineCountBadge` (trivial)

Straightforward `styled(View, {...})` port. Values (background, border,
radius, font) are hand-copied from the SCSS tokens' *resolved* output
(verified via `sass --load-path=.` against the actual `_colors.scss`/
`_variables.scss` maps, not guessed) - Tamagui has no visibility into the
SCSS token pipeline, so a real adoption needs its own token source of truth
(see #590), not a one-off copy like this PoC.

### `Button` (hard case) - passes, with one real gap found

- `apply-button-variant`'s three variants (primary/secondary/danger,
  including hover/press color) port cleanly onto Tamagui's
  `hoverStyle`/`pressStyle` variant keys.
- Used Tamagui's own `@tamagui/button` `Button` primitive as the base (it
  already renders a real `<button>` on web) rather than a raw stack, since
  `styled()` doesn't accept a bare HTML tag string directly.
- **Naming collision**: Tamagui's `Button` reserves the prop name `variant`
  for its own `'outlined'` style option. The app's `variant="primary"` API
  had to be renamed to `appVariant` to avoid silently colliding with that.
  Real friction for any component that already has a `variant` prop and
  adopts Tamagui's `Button` as a base.
- **The `$text-button` `md` breakpoint layer does carry over correctly -
  the original PoC pass here was wrong, and the fix was in my own
  verification method, not Tamagui.** `@tamagui/config`'s stock media
  breakpoints (`sm: 800`, `md: 1020`, ...) don't match this app's own scale
  (`sm: 576`, `md: 768` in `_variables.scss`), so `tamagui.config.ts`
  overrides `sm`/`md` to match. SCSS's `respond-to($bp)` defaults to
  `min-width` ("up"), while `respond-to($bp, down)` (used by
  `OnlineCountBadge`) reuses the *same* breakpoint name for a `max-width`
  query - one Tamagui media key can only ever mean one direction, so a
  second key (`mdUp: {minWidth: 768}`) was added for `Button`'s up-direction
  case.

  The first PoC pass measured `getComputedStyle()` on the outer `<button>`
  DOM node and saw an identical font size at 500px and 900px, and concluded
  the breakpoint wasn't applying. That was measuring the wrong element:
  Tamagui's `Button` is a compound component that forwards text-styling
  props (`fontSize`, `fontFamily`, `lineHeight`, `letterSpacing`,
  `textAlign`) to an inner `SizableText` **span child**, not the frame - the
  outer button never gets a `fontSize` class at all, static or responsive,
  by design. Re-checking the actual rendered span via a real Playwright
  build shows the breakpoint working exactly as authored: `_fos-1rem`
  (16px) at 500px width, `_fos-1--125rem` (18px) at 900px width, swapping
  cleanly on the `@media (min-width: 768px)` rule emitted into the compiled
  CSS. **Not a bug** - `apply-text-style`'s breakpoint layer is trustworthy
  here, provided any verification checks the element Tamagui actually
  applies text props to, not the frame.
- **A11y gap, verified via a failing test kept in the suite
  (`it.fails`, not silently passing or hidden):** Tamagui's `Button` sets
  `aria-disabled="true"` on `disabled` but does **not** set the native HTML
  `disabled` attribute the way the original `<button disabled>` does - the
  element stays focusable and clickable via keyboard/assistive tech unless
  every consumer also guards `onPress`. Confirmed with
  `expect(screen.getByRole('button')).toBeDisabled()` failing against real
  DOM output, not assumed from docs.

### `Tooltip` (primitive swap) - 1 pass / 2 fail, root cause verified for both

Unlike `@rn-primitives/tooltip` (#579's PoC), Tamagui's `Tooltip` **does**
expose a controlled `open` prop directly on the root, so no ref/imperative
`open()`/`close()` workaround was needed to keep this a drop-in replacement
for the app's existing controlled-open call sites - a genuine advantage
over the `@rn-primitives` PoC on this specific point.

Running this branch's actual 3-case `Tooltip.test.tsx` suite against the
swap:

| Case | Result |
|---|---|
| shows on hover, hides on pointer leave | **PASS** |
| shows on focus, wires `aria-describedby` | **FAIL** |
| dismisses on Escape | **FAIL** |

Both failures trace to the same root cause, confirmed by direct
diagnosis rather than assumed:

1. First diagnostic (forcing `open={true}`) proved the `Content` element
   and its `aria-describedby` wiring are correct in isolation - the
   trigger's `aria-describedby` does resolve to the floating wrapper's
   `id`, matching Radix's contract.
2. A **duplicate-role bug in this PoC's own code** was found and fixed
   along the way: the port initially set an explicit `role="tooltip"` on
   `Tooltip.Content`, which collided with the `role="tooltip"` Tamagui
   already sets on the floating portal wrapper around it, breaking every
   `getByRole('tooltip')` query with a "found multiple elements" error
   until removed. Worth flagging since it's an easy mistake to repeat and
   a subtle failure mode (looks like "won't open," not "renders twice").
3. With that fixed, hover opens/closes correctly. Focus does not, even
   with the documented opt-in (`focus={{ enabled: true }}`) set - the
   tooltip never opens on `user.tab()`.

**Follow-up dig (per discussion on the issue): confirmed this is a real
Tamagui bug, not a test-environment artifact like the breakpoint finding
above.** Re-verified against a real Chromium browser via Playwright (ruling
out happy-dom's `:focus-visible`/keyboard-modality simulation as the
cause, since that was the root cause of the breakpoint false-negative):
`Tab`-focusing the trigger in real Chromium does move focus (`document.
activeElement` is the trigger, and it does `matches(':focus-visible')` ===
`true`), but the tooltip's `data-state` stays `"closed"` and
`aria-expanded` stays `"false"` - the component genuinely never reacts to
focus, in a real browser, not just in tests.

Traced to source (`@tamagui/floating`, `@tamagui/popper` v2.6.0):
Tamagui's `Tooltip` builds an interaction-aware floating context via
`useFloatingContext()` - including a `useFocus()` hook wired to the
`focus={{ enabled: true }}` prop - and provides it down via
`FloatingOverrideContext`. But the underlying `Popper` primitive
(`@tamagui/popper/dist/esm/Popper.mjs`) builds its **own**, separate,
purely-positional `useFloating()` instance internally, and explicitly
resets `<FloatingOverrideContext.Provider value={null}>` around its own
children - discarding the focus-aware context Tooltip just built. `Popper
Anchor`'s `getReferenceProps()` (which is what would attach `onFocus`/
`onBlur` handlers to the real trigger DOM node) therefore always comes
from the interaction-less instance. Confirmed directly by instrumenting
`useFocus`'s `onFocus` callback with a `console.log`: it never fires at
all on `Tab`, in a real browser - not gated by a condition inside the
handler, never reached. (Hover still works because it's driven by
separate, hand-wired `onMouseEnter`/`onOpenChange` plumbing at the
Popover/Trigger level, unrelated to this broken interaction-props path -
which is exactly why hover passes while focus and Escape-driven dismiss,
which both depend on the same broken path, fail.)

This means `focus={{ enabled: true }}` is effectively **dead configuration**
in this version of Tamagui's Tooltip - it's accepted, plumbed partway
through, and then silently thrown away before reaching the DOM. Not
something an app-level workaround can easily patch (the break is inside
`@tamagui/popper`'s `Popper` component, not anything the app or the
Tooltip wrapper controls). Filed upstream as
[tamagui/tamagui#4152](https://github.com/tamagui/tamagui/issues/4152),
with the source-level root cause above included in the report. Until
that's resolved, a real adoption would need to either track that issue,
hand-roll the trigger's `onFocus`/`onBlur` to call the Tooltip's own
controlled `open` setter directly (bypassing the broken interaction-props
path entirely - untested here), or accept the accessibility gap.

## Visual parity

Confirmed by actually rendering both versions of `Button` (all three
variants) side by side via a throwaway Vite build + Playwright screenshot,
not by inspection alone. Colors, shape, and text render near-identically;
Tamagui's corners render very slightly less rounded than the SCSS
original's fully-pill shape at the same nominal `border-radius` value -
a minor, verified rendering difference, not a functional one.

## Recommendation

**Tamagui does not supersede #579's `@rn-primitives` recommendation.**
Reasons, all verified above rather than assumed:

1. **Bundle floor is ~4.5x heavier** for the same `react-native-web`-based
   web cost, because Tamagui bundles a full compiled-styling/token engine
   `@rn-primitives` doesn't - a real cost for an app that would still need
   its own token system anyway (per #590), not something the styling layer
   gets "for free" by adopting Tamagui.
2. **The one advertised win over `@rn-primitives` (controlled `open`) held
   up** - Tamagui's Tooltip doesn't need the ref/imperative workaround
   #579 had to build.
3. **The breakpoint story holds up, once corrected.** #591 flags Tamagui's
   token system as "a strong match on paper" for this app's
   `apply-text-style`/`apply-button-variant` mixins - both the variant-mixin
   part and the breakpoint part (`$mdUp`) hold up in this PoC. (An earlier
   pass of this doc incorrectly reported the breakpoint as broken; that was
   a measurement bug in the verification script - see the corrected note
   above - not a Tamagui limitation.)
4. **A11y parity has two verified gaps**, not zero: `Button`'s `disabled`
   state doesn't set the native HTML attribute, and `Tooltip`'s
   focus-to-open is a confirmed upstream bug, not a config miss or a test
   artifact - traced to source: `@tamagui/popper`'s `Popper` primitive
   discards the focus-aware interaction context Tooltip builds, before it
   ever reaches the trigger's DOM node. Re-verified in a real Chromium
   browser specifically to rule out the kind of test-environment
   false-negative the breakpoint finding turned out to be - this one holds.

**For #578/#591:** stay with #579's `@rn-primitives` recommendation.
Bundle size is a secondary concern on its own, and the breakpoint/variant
system is genuinely solid (corrected above), but Tooltip's focus-to-open
break is a confirmed defect inside `@tamagui/popper` itself, not something
fixable at the app level within this PoC's scope - `focus={{ enabled: true
}}` is accepted by the API and then silently discarded before it can do
anything. Adopting Tamagui's Tooltip today means either shipping without
keyboard-accessible tooltips, hand-rolling the trigger's focus/blur
handlers to bypass the broken path (untested, real engineering effort, not
a config flag), or waiting on an upstream fix - tracked at
[tamagui/tamagui#4152](https://github.com/tamagui/tamagui/issues/4152).
That's the one item that would need to be resolved - by Tamagui, not by
us - before this kit could be trusted with the app's Tooltip primitive.

## Companion Gluestack PoC

Still warranted, per the issue's framing - Gluestack's NativeWind-based
styling model is architecturally the opposite bet from Tamagui's compiled
runtime approach, so this PoC's bundle-floor and breakpoint findings don't
transfer. The a11y question is likely to look different too, since
Gluestack credits `@react-native-aria` rather than a from-scratch
Popper/floating-ui implementation - worth its own verification pass rather
than assuming the same gaps apply.

## Files changed on this branch

`tamagui.config.ts` (new), `vite.config.ts`, `src/main.tsx`,
`src/components/OnlineCountBadge/OnlineCountBadge.tamagui.tsx` (+ test),
`src/components/Button/Button.tamagui.tsx` (+ test),
`src/components/Tooltip/Tooltip.tamagui.tsx` (+ test), `.gitignore`
(`.tamagui/` compiler cache), `eslint.config.js` (ignore `.tamagui/`),
`package.json`/`package-lock.json` (new dependencies). The three `.tamagui`
PoC components are left as standalone files, not wired into the live app -
same "left in place as working evidence, not ready to merge" posture #579's
PoC took with its `Tooltip` swap.
