# Issue #579 — RN-compatible primitives library exploration

Scope: Question 1 of the spike ("adopt a library, or hand-roll?"), now
including the required PoC. `ds-entry.js` (Q2) has been separately decided:
it's WIP/aspirational, not a published contract — see corroborating evidence
at the end of this doc. No prop-compatibility obligation follows from it.

## What we currently use Radix for

`@radix-ui/react-*` (accordion, alert-dialog, dialog, dropdown-menu, popover,
progress, tabs, toast, tooltip) shows up in 11 files: `Tooltip`, `ToastManager`
/ `ToastContext`, `ProgressBar`, `Modal`, `AlertDialog`, `Navbar`,
`LibraryPage`, `FeedbackWidget`, `SupportFlow/ActivityInputScreen`. That
matches the nine primitives enumerated in #578 exactly — no hidden usage.

## Candidates

### 1. `@rn-primitives` (used by react-native-reusables / NativeWindUI)

- Ports Radix's primitive API to a universal surface: on web it wraps the
  real `@radix-ui/react-*` packages; on iOS/Android it ships native
  implementations of the same component contract (props, parts, a11y
  behaviour). One import per primitive (`@rn-primitives/dialog`, `.../toast`,
  etc.), fully unstyled — no design-system lock-in.
- **Coverage**: all nine of our primitives exist as separate packages
  (accordion, alert-dialog, dialog, dropdown-menu, popover, progress, tabs,
  toast, tooltip), plus extras we don't need (avatar, checkbox, select,
  slider, switch, table, menubar...).
- **Maintenance**: active. Packages published within the last two weeks as of
  this check (`portal` 7 days, `dialog` 4 days, `popover` 12 days, `label` 1
  day), MIT licensed, maintained by the same people behind
  react-native-reusables. Downloads range from ~30k/week (`utils`) to
  ~280k/week (`slot`, `portal`) — healthy adoption, not a one-person
  experiment.
- **Accessibility**: web side is literally Radix, so parity is exact by
  construction (focus trap/restore, roving tabindex, escape-to-close,
  `aria-*`) — nothing to reimplement or verify there. Native side reimplements
  the same behaviours against platform accessibility APIs (VoiceOver/TalkBack)
  rather than DOM `aria-*`, since RN has no ARIA; that's an inherent
  constraint of any RN primitive, not specific to this library.
- **Bundle cost**: revised after the PoC below — web is *not* unaffected in
  practice, because `react-native-web` itself is a real runtime, not a
  no-op shim.
- **Styling**: fully unstyled/style-agnostic — doesn't force a styling
  decision, so it doesn't collide with the separate styling-layer rework.
- **Caveat**: some packages have shipped un-transpiled JSX in the published
  output before (see `founded-labs/react-native-reusables#275`) — worth a
  quick build-compat check against our Vite/RN toolchain during the PoC
  rather than assuming it "just works".

### 2. React Native Reusables

Built on `@rn-primitives` + NativeWind, i.e. it's the primitives above plus a
shadcn-style component/styling layer. We'd be adopting more than we need —
overlaps with the separate styling-layer rework the same way a broader UI kit
would. Relevant mainly as evidence that `@rn-primitives` is proven in a real,
actively maintained downstream project, not as something to depend on
directly.

### 3. Tamagui / Gluestack UI (broader cross-platform kits)

Both solve components + a compiled/atomic styling system together (Tamagui
~180KB, Gluestack ~150KB added). Gluestack builds its a11y on
`@react-native-aria` (comparable rigor to Radix). Neither is a drop-in for
"just the nine primitives" — adopting either means also adopting its styling
system, which is explicitly the "broader UI kit" option the issue already
flags as a bigger commitment than this epic wants. Not recommended unless the
styling-layer rework decides to standardize on one of these anyway.

### 4. Hand-roll baseline (for comparison)

Still viable per the issue, but means reimplementing focus trap/restore,
roving tabindex, live regions, escape-to-close, and `aria-*` wiring for
Dialog/AlertDialog/Popover/DropdownMenu/Accordion/Tabs/Tooltip/Toast
ourselves, on both web and native, with our own a11y test coverage as the only
backstop. `@rn-primitives` removes essentially all of this work for the web
side (it's unmodified Radix) and reduces it to "verify their native a11y
implementation" for the RN side.

## PoC: swapping `Tooltip` to `@rn-primitives/tooltip`

Chose `Tooltip` over the suggested `ProgressBar`/`Toast` because neither of
those has an in-app consumer right now — a PoC needs a component under real
usage and real test coverage to mean anything. `Tooltip` has both: 6+
consumers app-wide and a 5-case test file covering exactly the interaction
model at risk (click/tap-to-toggle per #568, hover suppression, focus,
escape-to-close, `aria-describedby`).

Branch: `claude/rn-primitives-library-4ny4sa`. Changed: `Tooltip.tsx`,
`Tooltip.module.scss`, `vite.config.ts`, `package.json`.

**Result: all 5 existing tests pass, full unit suite unaffected (363
pass/12 pre-existing unrelated failures, identical with or without the
swap), production build succeeds.** Getting there required real work,
correcting three assumptions from the research above:

1. **Toolchain integration, not just an install.** `@rn-primitives` packages
   import from `react-native` and ship platform-specific files
   (`tooltip.web.mjs` vs `tooltip.mjs`) the way Metro/webpack resolve for
   react-native-web — Vite has no built-in notion of either. Needed:
   `resolve.alias` (`react-native` → `react-native-web`), a `resolve.extensions`
   list with `.web.mjs`/`.web.js` first, and a Vitest `deps.inline` override
   (Vitest externalizes `node_modules` to plain Node resolution by default,
   which can't do platform-extension resolution at all).
2. **Confirmed packaging bug.** The published `@radix-ui`-style `.mjs`/`.js`
   output contains raw, un-transpiled JSX (matches
   `founded-labs/react-native-reusables#275`, found during the earlier
   research). Needed a scoped esbuild-transform workaround in `vite.config.ts`
   to parse it at all — a real, currently-necessary patch, not a
   config nicety.
3. **`Root` has no controlled `open` prop.** Radix's `Tooltip.Root` (and our
   wrapper) is externally controlled — that's how #568's click/tap-to-toggle
   model works. `@rn-primitives/tooltip`'s `Root` manages open state
   internally and only exposes it via `onOpenChange` plus an imperative
   `open()`/`close()` pair on the **Trigger's ref**. The fix (switch our
   `setOpen` calls to `triggerRef.current?.open()`/`.close()`) is small, but
   it's a different control pattern per call site, not a drop-in prop
   rename — every consumer of a controlled Radix primitive in the app would
   need this same adjustment, not just Tooltip.

Smaller, non-blocking gaps also confirmed by writing the code (not just
reading types): no `Provider` part (fixed with a small context shim so the
app-level `<TooltipProvider>` call site didn't need to change) and no `Arrow`
part (hand-rolled a CSS-triangle replacement).

**Bundle cost, corrected.** Production build, `index` chunk, before vs. after
this one-primitive swap: 467.83 kB → 551.93 kB raw (145.02 kB → 173.94 kB
gzip) — **+84 kB raw / +29 kB gzip** to swap a single tooltip. That's mostly
the one-time cost of pulling in `react-native-web`'s runtime (View/Pressable/
StyleSheet shims) plus `zustand` (a `@rn-primitives/portal` dependency), not
a per-primitive cost — later primitives should add much less. But it means
"web bundle unaffected" (the research assumption above) was wrong; it's Radix
*wrapped in* react-native-web, not literally bare Radix.

## PoC: swapping a second primitive - `Popover` (`Navbar`'s announcements)

Extended the PoC to check whether Tooltip's two real frictions (bundle
one-time cost, controlled-`open` API mismatch) generalize across primitives,
or were specific to Tooltip. Chose `Popover` because it's a real in-app
consumer with existing test coverage: `Navbar`'s announcements popover
(`Navbar.tsx`), covered by `Navbar.test.tsx`'s click-to-open,
mark-all-read, and mark-one-read assertions. `Accordion` is used inside this
same popover's content but was left as Radix - only `Popover` itself was
swapped, to keep this a single-variable change.

**Result: this one was a clean, mechanical swap - a materially better
experience than Tooltip's.** Changed exactly one thing: the import
(`@radix-ui/react-popover` → `@rn-primitives/popover`). No component logic,
no styling, no test changes needed.

- **All 11 existing `Navbar.test.tsx` cases passed unmodified**, including
  the three real interaction tests (open on click, mark all read, mark one
  read) - not just render-only assertions.
- **Full unit suite: 363 pass / 12 fail, identical to the Tooltip-only
  baseline** - the 12 failures are the same pre-existing, unrelated
  `NavDrawer`/`LibraryPage` cases documented above, not anything from this
  change.
- **`@rn-primitives/popover`'s `Content` props (`side`, `align`,
  `sideOffset`) match Radix's one-for-one** - no adaptation needed, unlike
  Tooltip's `Arrow`/`Provider` gaps.
- **The controlled-`open` API mismatch (no `open` prop on `Root`, same as
  Tooltip) turned out not to matter here**, because `Navbar`'s existing
  Popover usage was already uncontrolled (`<Popover.Root>` with no
  `open`/`onOpenChange` props) - it only bit Tooltip because #568's
  click/tap-to-toggle rework specifically needed external control. This is
  the practical shape of the "audit every primitive for controlled-prop
  patterns" caveat in the original recommendation below: it's a real
  per-call-site risk, not a universal one - some call sites (like this one)
  simply don't hit it.
- **Bundle cost: +2.1 kB raw / +0.6 kB gzip** on top of the Tooltip-swap
  baseline (554.08 kB / 172.72 kB gzip, up from 551.94 kB / 172.09 kB gzip) -
  confirms the "later primitives should add much less" prediction above.
  Tooltip's +84 kB/+29 kB was genuinely a one-time `react-native-web`/
  `zustand` cost, not a per-primitive tax.
- Ran `npm run lint` after the change: same 4 pre-existing, unrelated
  issues as baseline (`ActivityRewardScreen.tsx`, `main.tsx`,
  `SuccessPage.tsx`, `vite.ds.config.js`) - nothing new.

## `ds-entry.js` (Q2) — corroborating evidence

Confirmed separately: `ds-entry.js` is WIP, not a real contract. Supporting
evidence found while running `npm run lint` for this PoC: `vite.ds.config.js`
already exists at the frontend root (a prior attempt at the missing lib
build CLAUDE.md/#579 asks about) and is currently broken —
`__dirname is not defined` (a CJS global used in an ESM config file). Nobody
has run this successfully recently; treating `ds-entry.js`'s four exports as
a preserved public API isn't warranted, and this is left as/for a separate
decision on deleting or properly wiring up the DS build (out of scope here).

## Recommendation

`@rn-primitives` is still the strongest fit for Question 1 — it covers all
nine primitives, doesn't force a styling decision, is actively maintained,
and both PoCs (Tooltip, Popover) came out passing with zero new test
failures. But it is not uniformly the "dependency swap + restyling, nothing
else" outcome the initial research suggested — the two PoCs show that
outcome varies per primitive rather than applying evenly:

- **Popover was a clean, mechanical swap** — one import line changed, all
  11 existing tests passed unmodified, `+2.1 kB raw / +0.6 kB gzip`.
- **Tooltip needed real adaptation work** — the controlled-`open` mismatch,
  missing `Provider`/`Arrow` parts, and the one-time `+84 kB raw / +29 kB
  gzip` `react-native-web`/`zustand` cost (a cost paid once, not per
  primitive - confirmed by Popover's near-zero marginal cost).

The deciding factor for Tooltip's extra cost wasn't the library, it was
that `Navbar`'s existing Popover usage happened to be uncontrolled, while
Tooltip's usage needed external control for #568's click/tap-to-toggle
model. Any adoption plan for #578 should budget for: pinning around (or
patching) the JSX packaging bug (confirmed present in both `@rn-primitives/
tooltip` and `@rn-primitives/popover`'s published output), the one-time
`react-native-web` bundle cost (paid once, not per primitive), and — the
one that actually varies per call site — auditing each of the remaining
seven primitives (`Dialog`, `AlertDialog`, `DropdownMenu`, `Accordion`,
`Tabs`, `Toast`, `Progress`) for whether its current usage relies on
controlled state the way Tooltip's does, since that's the one part of this
migration that isn't mechanical.

## Remaining next steps

1. Update per-primitive sizing estimates on the #578 sub-issues to reflect
   the corrected picture: most primitives look like Popover (near-mechanical
   swap), but any call site relying on controlled `open` state (confirmed:
   Tooltip; unconfirmed either way for the other seven) needs the
   Tooltip-style adaptation work budgeted instead.
2. Decide `ds-entry.js`'s fate (delete vs. properly wire up the build) as a
   separate, small piece of work — not blocking on this exploration.
3. Decide whether to keep this PoC's `Tooltip`/`Popover` swaps or revert
   them before any further #578 work — both are left in place on this
   branch as the working evidence for the above, not as something ready to
   merge as-is.
