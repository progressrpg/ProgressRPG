# Unified Timer — "Doing" / "Planning" Mode Switch — Implementation Plan

Base branch: `feat/unified-timer-task-mode-plan`, cut from `development` at
`2d200d18` (already includes the merged `UnifiedTimerHome` work — the prior
`unified-timer-homepage-plan.md` is fully implemented on `development`, not a
future dependency).

No new feature flag. `UnifiedTimerHome` is already gated end-to-end by
`unified_homepage` (`ActivityTimelinePage.tsx:10`); the mode switch is
additive UI inside that already-flagged tree, so a second flag would just be
extra ceremony around a sub-feature of something already dark-launched.

---

## Assumptions

1. "Timer page" = `UnifiedTimerHome` (the only place this brief makes sense —
   the legacy `CurrentActivity`/`ActivityTimeline` pair is out of scope and
   untouched, consistent with the original unified-homepage plan).
2. Mode switch is visible regardless of `isActive` — nothing in the brief
   restricts it to "only while a timer is running"; it says the *planning*
   mode is for managing tasks *while* the timer runs, not that the switch
   itself is hidden when idle. Defaulting to "doing" preserves today's
   behaviour byte-for-byte when the user never touches the switch.
3. Only two modes exist today ("doing", "planning") but the brief explicitly
   flags more arriving later — the chip control and the mode-storage shape
   must not hardcode a boolean.
4. "Tasks CRUD window below the activity label/input" means below the entire
   Row 1 + Row 2 control card (toggle/timer + label-or-search), not
   interleaved between them — that block is the identity of the running
   timer and shouldn't be split up.
5. Switching modes never stops or otherwise mutates the running timer —
   it's purely a view switch over the same `useActivityInput`/`useGame`
   state that already exists.

---

## 1. High-level strategy

Add a small piece of local UI state to `UnifiedTimerHome` — `mode: "doing" |
"planning"` — and a new chip-style switcher component to change it. Render
`TasksPanel` unmodified when `mode === "planning"`, below the existing
controls card. Everything else in `UnifiedTimerHome` (toggle, timer, label/
search row, support button) keeps rendering in both modes, since planning is
a *view added alongside* doing, not a replacement of the timer chrome — the
timer must stay visible/controllable while the user plans.

Two new small pieces, both additive:

- **`ModeSwitcher`**: a tiny new presentational component (chip group,
  `role="radiogroup"`) — there's no existing segmented-control/tab component
  in the frontend to reuse (checked: no chip/segmented/tab pattern exists
  outside ad-hoc buttons), so this is a genuinely new, minimal component
  rather than a duplicate of something already there.
- **Local `mode` state in `UnifiedTimerHome`**: `useState<TimerMode>("doing")`,
  no persistence beyond the session — resets to "doing" on reload, matching
  how `isEditingLabel`/`submitConfirmOpen` are already handled as ephemeral
  UI state in this component rather than round-tripped anywhere.

`TasksPanel` is reused wholesale, unmodified — no prop changes, no new
"embedded" variant. Its own `<div className={styles.page}>` wrapper uses the
`page-layout` mixin (`padding: v.$padding-base`, `max-width: 1000px/576px`
per child) — nested inside `UnifiedTimerHome`'s own `max-width: 720px`
wrapper, the inner max-width never binds (720 < 1000), so the only visible
effect is one extra padding ring, which is acceptable and avoids forking the
component.

---

## 2. Files likely to change

| File | Change | Exists? |
|---|---|---|
| `frontend/src/components/UnifiedTimerHome/UnifiedTimerHome.tsx` | Add `mode` state, render `ModeSwitcher`, conditionally render `TasksPanel` | Yes, extend |
| `frontend/src/components/UnifiedTimerHome/UnifiedTimerHome.module.scss` | Layout for the switcher row + planning-mode panel spacing | Yes, extend |
| `frontend/src/components/UnifiedTimerHome/UnifiedTimerHome.test.tsx` | New tests for mode switching | Yes, extend |
| `frontend/src/components/ModeSwitcher/ModeSwitcher.tsx` | New chip-group component | New |
| `frontend/src/components/ModeSwitcher/ModeSwitcher.module.scss` | New | New |
| `frontend/src/components/ModeSwitcher/ModeSwitcher.test.tsx` | New | New |
| `frontend/src/components/TasksPanel/*` | **No changes** — reused as-is | Existing, untouched |

No backend, hook (`useActivityInput`/`useActivityTimer`/`useTasksPanel`), or
routing changes — this is a pure presentational addition on top of state that
already exists (`useTasksPanel` already has everything the CRUD window
needs; `useGame`'s `activityTimer` is unaffected by which mode is showing).

---

## 3. Implementation plan

**Phase 1 — `ModeSwitcher` component**
- Generic chip-group: `modes: { key: string; label: string }[]`,
  `activeKey: string`, `onSelect: (key: string) => void`.
- Renders a `role="radiogroup"` wrapper with one button per mode
  (`role="radio"`, `aria-checked`), styled as pill/chip buttons — active chip
  visually distinct (matches existing `Button` `variant` convention: reuse
  the same primary/secondary color tokens `TasksPanel`'s `filterToggle`
  already uses, rather than inventing new colors).
- Deliberately generic over the mode list (not hardcoded to "doing"/
  "planning") so a third mode later is a data change, not a component change.
- Full ARIA radiogroup keyboard behaviour (per Open questions, resolved):
  only the active chip is a Tab stop (`tabIndex={0}`, others `-1`); Left/Up
  and Right/Down move selection to the previous/next chip (wrapping at the
  ends); Home/End jump to the first/last chip. Arrow/Home/End both move
  focus and fire `onSelect` together, matching the standard "selection
  follows focus" radiogroup pattern.
- Unit tests: renders a chip per mode; `aria-checked`/`tabIndex` reflect
  `activeKey`; click calls `onSelect` with the right key; arrow key
  navigation moves selection and wraps at the ends; Home/End jump to
  first/last chip.

**Phase 2 — wire `mode` state into `UnifiedTimerHome`**
- `const [mode, setMode] = useState<"doing" | "planning">("doing");`
- Render `<ModeSwitcher modes={[{key: "doing", label: "Doing"}, {key:
  "planning", label: "Planning"}]} activeKey={mode} onSelect={setMode} />`
  directly under the existing controls card (`.container`), above the
  auto-stop warning / support button row.
- When `mode === "planning"`, render `<TasksPanel />` below the switcher;
  when `"doing"`, render nothing extra — today's output.
- No change to `showLabelDisplay`/`statusMessage`/toggle logic — those stay
  keyed off `isActive`/`isUnlabelled` exactly as today, independent of
  `mode`.
- Component tests: default mode is "doing" (no `TasksPanel` in the tree);
  clicking the "Planning" chip renders `TasksPanel`; switching back to
  "Doing" unmounts it; timer controls (`Start`/`Stop`, elapsed time) remain
  visible and functional in both modes.

**Phase 3 — layout/spacing polish**
- SCSS for the switcher row (small gap above/below, centered or left-aligned
  to match the card's existing rhythm) and for the planning panel's
  top margin so `TasksPanel`'s own padding doesn't look cramped against the
  switcher.
- Manual QA: switch modes while a timer is running and while idle; confirm
  no layout jump in the controls card itself (only content *below* it should
  change) — reuses the same "row 1 never reacts to row 2" principle already
  established in `UnifiedTimerHome.module.scss`.

**Phase 4 — accessibility pass**
- `aria-live` region update (or confirm the existing one) so switching modes
  doesn't need a separate announcement beyond the radiogroup's own state
  change; verify focus doesn't jump unexpectedly when `TasksPanel` mounts.
- Playwright/a11y test extending existing `/timer` coverage: flag-on, switch
  to Planning, add/complete/delete a task inline, switch back to Doing.

---

## 4. Design decisions

**1. New small `ModeSwitcher` component vs. reusing `Button` in a row.**
Alternative: two adjacent `Button` components with manual active-state
styling. Rejected — a two-way (soon N-way) exclusive-choice control is
semantically a radiogroup, not two independent buttons; getting
`aria-checked`/keyboard behavior right once in a dedicated component is
cheaper than re-deriving it at every call site, and this brief explicitly
asks for "some sort of chip visual," i.e. a recognizable, reusable pattern —
not a one-off. Scoped as its own component (not inlined in
`UnifiedTimerHome`) so the "more modes in future" requirement doesn't force
edits to the host component later.

**2. Mode state lives in `UnifiedTimerHome`, not in `useActivityInput`.**
Alternative: add `mode`/`setMode` to `useActivityInput` alongside
`isEditingLabel` etc. Rejected — `useActivityInput` is shared timer/activity
business logic consumed elsewhere (`ActivityInput.tsx` legacy tree, `Support
Flow`); "which view is currently showing" is presentational state specific
to `UnifiedTimerHome`'s layout, with zero bearing on activity/timer
behaviour. Keeping it local avoids widening a shared hook's surface for a
concern that only one consumer has, and matches how `submitConfirmOpen` is
already local to the component for the same reason.

**3. Render `TasksPanel` unmodified vs. extracting a props-driven "embedded"
variant.**
Alternative: add an `embedded`/`hideChrome` prop to `TasksPanel` to strip its
outer `page-layout` wrapper. Rejected for a first pass — the only visible
cost of not doing this is one extra padding ring (quantified in strategy
section above), which is a minor visual nit, not a functional problem.
Forking `TasksPanel`'s rendering behind a prop is exactly the kind of
premature abstraction the brief's "reuse as much as possible" points away
from; if the padding genuinely looks wrong in manual QA (Phase 3), the fix
is a single optional prop added then, with evidence, not speculatively now.

**4. No persistence of the selected mode (resets to "doing" on reload).**
Alternative: persist to `localStorage` (`TasksPanel` already has precedent
for this with `TASKS_HIDE_COMPLETED_KEY`). Rejected for v1 — the brief
describes this as "the first version of task mode"; defaulting to "doing"
every load keeps the change fully invisible to anyone who never touches the
switch, and persistence is a one-line follow-up once the mode-switching
mechanism itself is validated. Flagged as a likely fast-follow, not a gap.

---

## 5. Edge cases

- **Switching to Planning mid-timer, then stopping the timer from within
  Planning mode**: the Stop button lives in the controls card, which renders
  in both modes (Design/Strategy above), so this works without extra
  wiring — `handleToggle` doesn't know or care what `mode` is.
- **Starting a task from within `TasksPanel`'s row-action (▷ "start working
  on this task") while already in Planning mode with a *different* timer
  running**: `useTasksPanel.handleStartTask` already guards on
  `activityTimer?.status === "active"` and no-ops if so (existing behaviour,
  untouched) — worth an explicit test since this is the one place the two
  panels' state can collide.
- **Rapid mode toggling**: pure client-side state flip, no network calls, no
  race conditions to guard against.
- **Mode switch while `isEditingLabel` is true (click-to-edit in
  progress)**: switching to Planning mid-edit doesn't call `handleLabelBlur`
  or `handleLabelCancel` — the edit state is preserved and still resolves
  normally if the user switches back to Doing and blurs/confirms. Worth a
  test to confirm `isEditingLabel` isn't reset by the mode change (it
  shouldn't be, since `mode` and `isEditingLabel` are independent state, but
  this is an easy thing to accidentally couple).
- **Empty task list in Planning mode**: already handled by `TasksPanel`'s
  existing empty state — no new work.

---

## 6. Tests

**Frontend unit (Vitest)**
- `ModeSwitcher`: renders one chip per mode; `aria-checked` reflects
  `activeKey`; click calls `onSelect(key)`; renders correctly for 2 and 3+
  modes (guards against hardcoding the two-mode case).

**Frontend component (RTL)**
- `UnifiedTimerHome`: defaults to Doing (no `TasksPanel` rendered); clicking
  the Planning chip mounts `TasksPanel` and keeps the controls card
  (Start/Stop, timer) rendered and functional; switching back to Doing
  unmounts `TasksPanel`; `isEditingLabel` state survives a mode round-trip
  (edge case above).

**E2E (Playwright)**
- Extend the existing flag-on `/timer` spec (kept isolated from the flaky
  spec per project memory, same as the original unified-homepage plan): start
  a timer, switch to Planning, add a task, mark it complete, switch back to
  Doing, stop the timer — confirms no interference between the two panels'
  state.

---

## 7. Risks

- **Padding/visual mismatch from nesting `TasksPanel` as-is** (Design
  decision 3) — low risk, but flag it explicitly in the PR description so
  the reviewer checks it visually rather than assuming it's pixel-perfect
  merely because it compiles.
- **Accidentally coupling `mode` to `isActive`** — e.g. auto-switching back
  to "Doing" on Stop, which isn't asked for and would surprise a user who's
  mid-way through planning tasks around a just-finished timer. Keep the two
  fully independent.
- **Radiogroup a11y correctness** — this is the first `role="radiogroup"` in
  the frontend (no existing precedent to copy from), so it's easy to get the
  roving-`tabIndex`/arrow-key/Home-End behaviour subtly wrong (e.g. making
  every chip a separate Tab stop instead of one roving stop). Worth explicit
  reviewer attention since there's no local example to diff against.

---

## 8. Open questions

All resolved:

1. **Keyboard semantics**: implement full radiogroup behaviour in Phase 1 —
   arrow keys (Left/Right or Up/Down) move selection between chips, Home/End
   jump to first/last, matching the standard ARIA radiogroup pattern (only
   the active chip is in the Tab order; arrow keys move focus + selection
   together). Since there's no existing precedent in this codebase, Phase 1
   implements this from the ARIA APG radiogroup pattern directly rather than
   copying local code.
2. **Visual spec**: match existing styling — same color tokens/border
   treatment as `TasksPanel`'s `filterToggle` (`Button` secondary/primary
   variant colors), no new colors or icons introduced.
3. **Persistence**: confirmed — default to `"doing"` every load, no
   `localStorage` persistence in v1 (Design decision 4 stands as written).

None outstanding — implementation can proceed through Phase 4 without
further product input.
