# Radix → Tamagui migration: accessibility parity checklist

Tracks the accessibility verification for #578 (epic: replace Radix UI with
Tamagui) per #587's acceptance criteria. Captures what was checked, how, and
what's explicitly deferred - not a rubber stamp. Reusable as a template for
the styling and routing migrations that follow (#587's own ask); copy the
table structure and re-run the same passes.

## Status

**Dependency removal is complete** - all nine `@radix-ui/*` packages are
gone, including `react-dialog` (`DetailSurface.tsx`, per the plan at
`.claude/plans/issue-799-detailsurface-tamagui-plan.md` and
[#799](https://github.com/progressrpg/ProgressRPG/issues/799)).

**Still not fully closed** on the verification half: several steps this
checklist calls for need infrastructure this sandbox doesn't have (a
running Django backend, a real touch device, a screen reader, a matching
Playwright browser build for Storybook's a11y addon) - marked **Not run
here** below, with what *was* possible run in its place.

## Dependency removal

Nine `@radix-ui/*` packages before this migration started. Current state:

| Package | Status |
|---|---|
| `@radix-ui/react-toast` | Removed (#581) |
| `@radix-ui/react-alert-dialog` | Removed (#582) |
| `@radix-ui/react-tooltip` | Removed (#583) |
| `@radix-ui/react-tabs` | Removed (#584) |
| `@radix-ui/react-progress` | Removed (prior to this migration's sub-issues, per `package.json` history) |
| `@radix-ui/react-accordion` | Removed (#587 - unused since #586) |
| `@radix-ui/react-dropdown-menu` | Removed (#587 - unused since #586) |
| `@radix-ui/react-popover` | Removed (#587 - unused since #585/#586) |
| `@radix-ui/react-dialog` | Removed (#799 - `DetailSurface.tsx` ported to Tamagui's `Dialog`) |

`grep -rn "@radix-ui" frontend/src` now returns exactly one hit: a comment
in `Tabs.tsx` that documents what shape it mirrors, not an import.

### Bundle-size delta

Two separate measurements, both direct (`dist/` total + gzip size,
before/after, same build):

- **#587** (removing `react-accordion`, `react-dropdown-menu`,
  `react-popover`): **0 bytes**. Expected - none of the three were imported
  by any code after #585/#586, so Vite's bundler was already excluding them
  from the shipped bundle; removing them from `package.json` was a
  dependency-hygiene and `npm ci` cleanliness win, not a bundle-size one.
- **#799** (removing `react-dialog`, the last of the nine, after porting
  `DetailSurface.tsx` to Tamagui's `Dialog`): **-36,496 bytes raw / -12,180
  bytes gzip**. This one *was* actually bundled (it was genuinely imported),
  so removing it produced a real, reproducible reduction - unlike #587's
  zero-byte result.

The real bundle cost of the Tamagui migration itself was already measured
and recorded in #629 (+383 kB raw / +102 kB gzip fixed cost from wiring in
the provider, before any primitive was ported) - neither of the
measurements above changes that number; they're just the Radix-removal
side of the ledger.

## Toolchain

The `@tamagui/vite-plugin` config this migration settled on (per #629,
finalized rather than the abandoned `@rn-primitives` toolchain #579
originally scoped for):

- `@tamagui/vite-plugin` wired into `vite.config.ts` (`tamaguiPlugin({config: './tamagui.config.ts', components: ['tamagui']})`)
- `tamagui.config.ts` at the repo root
- `<TamaguiProvider>` mounted at the app root (`src/main.tsx`)
- `.tamagui/` (compiler cache) already in both `.gitignore` and
  `eslint.config.js`'s `globalIgnores`

No further action needed here - already finalized, not a leftover
`@rn-primitives`-era workaround.

Final Tamagui dependency set, confirmed present in `package.json`:
`tamagui`, `@tamagui/core`, `@tamagui/config`, `@tamagui/vite-plugin`,
`react-native-web` - matching #587's own list.

## Remaining Radix usage

None. `frontend/src/components/DetailSurface/DetailSurface.tsx` - the Map
entity detail card's dialog primitive, used by both `MapDetailCard` call
sites in `Map.tsx` - was the last one, resolved in #799.

**What made it harder than the other eight**: both `MapDetailCard` call
sites always pass a `container` prop (the map's own wrapper element) so the
detail panel portals there instead of `document.body` - needed for the
non-modal docked panel to position relative to the map (`position: absolute`
against `.mapWrapper`'s `position: relative`), not the viewport. Tamagui's
web `Portal` hardcodes `createPortal(children, document.body)` with no
per-instance override, unlike Radix's `Dialog.Portal`. Resolved by bypassing
`Dialog.Portal` only when a `container` is supplied, portaling
`Dialog.Content` there directly via `ReactDOM.createPortal` (still a React
context descendant of `<Dialog>`, so open/close/dismiss wiring keeps
working), gated on `open` in `DetailSurface`'s own code - `Dialog.Content`
doesn't gate its own mounting on `open` (that's `Dialog.Portal`'s job
internally), so skipping `Portal` without adding that gate back would have
left the docked panel sitting in the DOM at all times, non-interactive but
still visible. Caught and fixed before merging, not after - see the plan
doc (`.claude/plans/issue-799-detailsurface-tamagui-plan.md`) for the full
reasoning and alternatives considered, and #799's own PR for the real-browser
verification (DOM containment, correct docked positioning, and correct
unmount-on-close, confirmed against a harness reproducing `.mapWrapper`'s
actual CSS).

## Known, recorded gaps

Two gaps #587 asked to be confirmed one way or the other, not silently
inherited:

- **Tamagui's own `Button` sets `aria-disabled` but not the native
  `disabled` attribute.** Doesn't apply here - grepped `frontend/src` for
  any import of Tamagui's `Button` and found none. Every component in this
  app (`AlertDialog`, `Modal`, `Popover`, `DropdownMenu`, etc.) uses this
  app's own `components/Button/Button.tsx`, which sets both `disabled` (the
  real DOM attribute, for `as="button"`) and `aria-disabled` correctly.
- **Tooltip's focus-to-open gap** ([tamagui/tamagui#4152](https://github.com/tamagui/tamagui/issues/4152))
  - resolved with a workaround, not upstream-fixed: `Tooltip.tsx`'s
  `handleFocusCapture` intercepts in the capture phase specifically because
  Tamagui's own bubble-phase `onFocus` is broken (see the comment there,
  which cites both #583 and the upstream issue). Popover and DropdownMenu
  share `@tamagui/popper` for positioning but not the hover/focus
  interaction code the bug is in - neither uses hover-to-open, both are
  click-driven - so the same bug doesn't reach them; nothing to work around
  there.

## Per-component verification

Legend: ✅ verified in this sandbox · 📝 verified via reasoning/code
inspection (see linked PR/component for detail) · ⛔ not runnable here, see
[What couldn't be verified here](#what-couldnt-be-verified-here).

| Component | Keyboard pass | Focus restore | Screen reader | Touch | Notes |
|---|---|---|---|---|---|
| Toast (#581) | 📝 (own PR) | n/a (non-modal) | ⛔ | n/a | See PR #702 |
| AlertDialog/Modal (#582) | ✅ `AlertDialog.test.tsx`/`Modal.test.tsx` | ✅ (`useReturnFocusOnClose`, tested) | ⛔ | n/a | |
| Tooltip (#583) | ✅ `Tooltip.test.tsx` | n/a (no trap) | ⛔ | ✅ click/tap-to-toggle, tested | Focus-to-open gap, see above |
| Tabs (#584) | ✅ roving tabindex, real-browser verified per PR #793 | n/a | ⛔ | n/a | |
| Popover/FeedbackWidget (#585) | ✅ `Popover.test.tsx` | ✅ tested | ⛔ | ✅ real-browser harness, PR #797 | |
| Popover/Accordion/DropdownMenu in Navbar (#586) | ✅ `DropdownMenu.test.tsx`, `Navbar.test.tsx` (arrow keys, Escape, multi-open accordion) | ✅ tested | ⛔ | ✅ real-browser touch-emulated harness, PR #798 - found and fixed a real tap-to-open bug (`asChild` + coarse pointer) | Flagged in PR #798 for a real-phone check given the bug found there |
| ProgressBar | 📝 no interactive semantics to trap/restore | n/a | ⛔ | n/a | |
| DetailSurface/DetailCard/MapDetailCard (#799) | ✅ `DetailSurface.test.tsx`, `DetailCard.test.tsx` (Escape, outside-click gating by `modal`) | ✅ tested (`useReturnFocusOnClose`, reused from Modal/AlertDialog) | ⛔ | n/a (no touch-specific behaviour; container-portal positioning verified in a real browser instead, see below) | Real-browser harness confirmed the docked panel renders as a DOM descendant of a `.mapWrapper`-equivalent container, docks at the expected position (not the viewport), and correctly unmounts (not just goes non-interactive) on close - MapLibre itself still not renderable in this sandbox, so this used a harness reproducing the real CSS/positioning contract rather than the live Map page |

## What couldn't be verified here

Recorded explicitly per #587's own ask ("any accepted regression recorded
explicitly with reasoning, rather than silently absorbed") - these aren't
skipped by choice, they're infrastructure this sandbox doesn't have:

- **`npm run test:a11y`** (axe-core via Playwright) - blocked by no running
  Django backend to authenticate against (`ECONNREFUSED 127.0.0.1:8000`).
  Same limitation documented in #582/#583/#585/#586.
- **`npm run test:storybook`** (Storybook's a11y addon, run via Vitest
  browser mode) - blocked by a pre-existing Playwright headless-shell
  version mismatch in this sandbox's browser install, unrelated to this
  migration. Same limitation documented in #582/#583/#584.
- **Screen-reader pass** (NVDA/JAWS/VoiceOver/Orca) over toasts, dialogs,
  tabs, accordion - no screen reader available in this sandbox. ARIA
  attributes for each (role, aria-expanded/selected/live, etc.) were
  verified via jsdom + real-browser DOM inspection instead (see each
  component's own PR), which catches incorrect/missing attributes but not
  announcement politeness or phrasing.
- **Real touch-device pass** - no physical touch hardware in this sandbox.
  Playwright's touch/mobile emulation was used instead (see #585/#586 PRs)
  and, in #586's case, caught a real bug emulation-only testing would have
  otherwise missed if taken as sufficient on its own - which is exactly why
  this row stays ⛔ rather than being upgraded to ✅ on emulation alone.

## Reusing this checklist

For a future migration (styling, routing, or otherwise):

1. Copy the "Per-component verification" table, one row per component
   touched.
2. For each: run its unit tests (keyboard, focus restore), grep for the
   library being replaced to confirm the swap is complete, and do a
   real-browser pass (Playwright with the pinned executable if
   `test:storybook`/`test:a11y` aren't runnable) for anything jsdom can't
   observe - positioning, touch/pointer-type-conditional behaviour, real
   focus movement.
3. Record every gap found against the library being replaced explicitly,
   even ones judged safe to accept - this doc's "Known, recorded gaps"
   section is the model.
4. Update the "What couldn't be verified here" section for whatever
   infrastructure is actually available in the environment you're running
   in - it won't always be the same gaps.
