# Issue #579 — RN-compatible primitives library exploration

Scope: Question 1 of the spike only ("adopt a library, or hand-roll?"). This
is a research note, not the full spike decision — it doesn't cover the
`ds-entry.js` question (Q2) or produce the required PoC. Both are called out
as next steps.

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
- **Bundle cost**: web bundle is unaffected for the parts we already ship
  (still Radix under the hood); native platforms only pay for what RN needs,
  since it's tree-shakeable per-primitive packages rather than a monolith.
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

## Recommendation

`@rn-primitives` is the strongest fit for Question 1: it covers all nine
primitives with a compatible, unstyled API; it doesn't force a styling
decision; web accessibility is Radix itself (zero regression risk there); and
it's actively maintained with real downstream adoption. It converts most of
epic #578 from nine rewrites into a dependency swap + restyling, which is the
outcome the issue says is worth checking hardest for.

## Next steps (not done here — larger than this exploration)

1. **PoC** (per acceptance criteria): replace `ProgressBar` or `Toast` end to
   end with `@rn-primitives`, including a11y tests, before committing to this
   choice for the whole epic. This is the fastest way to catch the JSX/build
   issue above or any other integration surprise.
2. Answer Q2 (`ds-entry.js` contract) — independent of this decision, but
   both need answering before #578's sub-issues can be sized.
3. If the PoC passes, update per-primitive sizing estimates on the #578
   sub-issues to reflect "swap + restyle" rather than "rewrite."
