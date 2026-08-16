# Plan: Results mode for unified timer (issue #633)

## 1. High-level strategy

Extract the reward-breakdown rendering (XP/multipliers/level-ups) out of
`ActivityRewardScreen.tsx` into a new presentational component
(`RewardBreakdown` or similar) that takes normalized primitive props only —
no hook calls, no modal-width assumptions. `ActivityRewardScreen` keeps its
modal-specific chrome (countdown-to-support, `useTasks`/`useUpdateTask`/`useGame`
data fetching, constrained width via the existing Modal wrapper) and consumes
the extracted piece.

Add a `results_mode` feature flag. On the unified timer
(`UnifiedTimerHome` / `useActivityInput`), add a fourth derived UI state,
"Results", entered when `handleToggle` (manual stop) or
`useAutoStopCompletionEffect` (auto stop) fires. When `results_mode` is on,
these two call sites set local Results state directly with the reward data
instead of calling `openActivityReward(...)` (which opens the SupportFlow
modal via `OPEN_ACTIVITY_REWARD`). When the flag is off, current behavior
(dispatch to SupportFlow modal) is unchanged.

The Results state renders a new `TimerResultsPanel` component, itself built
on top of the extracted `RewardBreakdown`, plus timer-specific bits: the
"You spent X minutes on Y" copy with live debounced relabeling, inline
labeling entry point, task complete/undo toggle re-using the same
`useUpdateTask` pattern, and manual-only exit back to Input.

This keeps the state-machine style already used in `useActivityInput`
(booleans/derived state, not a formal reducer) rather than introducing a new
abstraction, consistent with how `isActive`/`isUnlabelled`/`isEditingLabel`
work today.

## 2. Files likely to change

- `frontend/src/components/SupportFlow/screens/ActivityRewardScreen.tsx` —
  extract breakdown JSX/logic into the new shared component; existing file
  shrinks to: countdown/support-panel chrome + task fetch/update + rendering
  the shared component. Existing.
- `frontend/src/components/SupportFlow/screens/RewardBreakdown.tsx` (name TBD)
  — new presentational component: base XP, premium/task multiplier lines,
  total XP row, level-ups. New file.
- `frontend/src/components/SupportFlow/screens/RewardBreakdown.module.scss`
  (or reuse `SupportFlowModal.module.scss` classes if styling is identical) —
  new/likely reused, decide during implementation.
- `frontend/src/components/UnifiedTimerHome/UnifiedTimerHome.tsx` — render
  Results panel when in Results state instead of (or alongside gating)
  `SupportFlowModal`. Existing.
- `frontend/src/components/UnifiedTimerHome/TimerResultsPanel.tsx` — new
  component: activity-name copy w/ debounced relabel, task summary +
  complete/undo toggle, unlabeled inline labeling, upgrade prompt, exit
  button. Consumes `RewardBreakdown`. New file.
- `frontend/src/components/UnifiedTimerHome/TimerResultsPanel.module.scss` —
  new.
- `frontend/src/components/ActivityInput/useActivityInput.ts` — add Results
  local state (e.g. `resultsData: ResultsPayload | null`), branch the two
  `openActivityReward(...)` call sites (manual stop `handleToggle` line ~331,
  auto-stop `useAutoStopCompletionEffect` line ~124) on `results_mode` flag:
  when on, set `resultsData` instead of dispatching `OPEN_ACTIVITY_REWARD`;
  add `exitResults()` to clear it (manual-only exit, no countdown). Existing.
- `frontend/src/types/enums.ts` — add `"results_mode"` to `FeatureFlagKey`.
  Existing.
- `frontend/src/featureFlags.ts` — add `results_mode: []` default-off entry.
  Existing.
- `frontend/src/components/SupportFlow/supportFlowReducer.ts` /
  `supportFlowTypes.ts` — no change expected; SupportFlow's own reducer
  keeps working as-is for the flag-off path. Existing, unchanged unless the
  extraction reveals shared normalization logic worth factoring into a
  small pure helper (e.g. `computeRewardBreakdown(ctx)`).
- Tests (see section 6).

## 3. Implementation plan

Small, reviewable commits in this order:

1. **Extract `RewardBreakdown`** from `ActivityRewardScreen.tsx`: pure
   component taking `{ baseXp, xpMultiplier, taskXpMultiplier, xpGained,
   levelUps }`, no hooks, no modal-width wrapper. Update
   `ActivityRewardScreen` to render it. No behavior change — existing
   `ActivityRewardScreen.test.tsx` should still pass unmodified (or with
   minimal import updates). This isolates the risky refactor from any new
   feature work.
2. **Add `results_mode` feature flag** (enums + default fallback), following
   the exact pattern used for `unified_homepage`. No UI change yet.
3. **Add Results local state to `useActivityInput`**: introduce
   `resultsData` state and `exitResults()`; branch the two stop call sites
   on `useFeatureFlag("results_mode")` to populate `resultsData` instead of
   `openActivityReward(...)` when the flag is on. Export
   `resultsData`/`exitResults` from the hook. Flag is off in default configs,
   so this is inert until step 5 renders it.
4. **Build `TimerResultsPanel`**: renders `RewardBreakdown` plus
   activity-name copy, task summary/complete-undo toggle (reusing
   `useUpdateTask` the same way `ActivityRewardScreen` does), unlabeled
   inline-labeling entry point with ~1s debounced update, upgrade prompt
   (reuse the same condition logic as `ActivityRewardScreen`, likely
   extracted alongside `RewardBreakdown` or duplicated minimally — decide in
   design step below), and an exit button calling `exitResults()`.
5. **Wire into `UnifiedTimerHome`**: when `resultsData` is set, render
   `TimerResultsPanel` in place of the normal timer body; otherwise render as
   today. Ensure `SupportFlowModal` still renders normally for the flag-off
   path (its `openActivityReward` dispatch untouched).
6. **Inline relabeling wiring**: connect `TimerResultsPanel`'s label input to
   the existing activity-naming mutation path (reuse whatever
   `handleConfirmActivity`/label-update call `useActivityInput` already
   exposes) with debounce, and surface the task-summary section immediately
   once a task becomes linked.
7. **Tests** for each of the above (see section 6), plus Playwright e2e flow
   with `results_mode` flag on.
8. **Docs**: if `docs/architecture/repo-structure.md`'s tree listing needs
   updating for new files, update it in the same PR that adds them.

## 4. Design decisions

**Where does Results state live?**
- Chosen: local state inside `useActivityInput` (a sibling to
  `isEditingLabel`), not a new reducer action on `supportFlowReducer`.
- Alternative: add a `RESULTS` screen to the SupportFlow reducer/modal and
  render it un-modal'd.
- Reasoning: SupportFlow's reducer/modal is purpose-built for the modal
  overlay (countdown-to-support, screen stack, `SUPPORT_MENU` etc.) which
  Results explicitly must NOT have (manual-only exit, no auto-continue, no
  modal chrome). Reusing that reducer would require carrying flags through
  it to suppress modal-only behavior — more coupling, not less. A local
  state slot in the hook that already owns the stop call sites is simpler
  and keeps the flag-off path (SupportFlow) completely untouched.

**Shared component scope: breakdown only, vs. breakdown + upgrade prompt +
task toggle?**
- Chosen: extract just the reward-breakdown (XP/multipliers/level-ups) as
  `RewardBreakdown`; keep upgrade-prompt condition logic and task
  complete/undo as separate, duplicated-but-small logic in each of
  `ActivityRewardScreen` and `TimerResultsPanel`.
- Alternative: one large shared component covering everything (breakdown +
  task toggle + upgrade prompt), parameterized by mode.
- Reasoning: the issue explicitly asks to extract "reward-breakdown
  rendering" logic, not the whole screen. Task toggle and upgrade prompt
  have different surrounding context in each host (modal panel vs. inline
  timer panel) and different exit/countdown behavior nearby; forcing them
  into one shared component adds conditional branches for behavior that's
  actually different per host (countdown pause-on-hover only applies to the
  modal). Keeping the breakdown extraction narrow matches "decouple from
  modal-specific styling/prop shape" from the issue without over-abstracting.
  If duplication of the upgrade-prompt condition (`showUpgradePrompt &&
  !isLikelyPremiumUser`) becomes annoying, it can be pulled into a tiny pure
  helper function (not a component) shared by both — cheap to do, avoid
  doing it prematurely.

**Feature flag scope: gate only the modal-vs-panel choice, or gate more?**
- Chosen: `results_mode` flag controls exactly one branch point — whether
  the two stop call sites in `useActivityInput` populate `resultsData` or
  dispatch `openActivityReward`. Everything else (extraction, new
  components) ships unconditionally since it's inert when unused.
- Reasoning: minimizes flag-checked surface area, consistent with
  `unified_homepage`'s single gating point in `ActivityTimelinePage.tsx`.

**Debounced live relabel — reuse existing debounce utility or add one?**
- Check `frontend/src/hooks`/`utils` for an existing debounce hook before
  adding a new one (issue specifies ~1s after last keystroke, matching a
  common UX debounce pattern already likely used elsewhere in the app,
  e.g. search/autocomplete inputs). Reuse if present; otherwise a small
  local `useDebouncedCallback`-style helper, not a new dependency.

## 5. Edge cases

- Manual stop with no activity name and no task at all (`isUnlabelled`
  through to stop) → Results shows "an activity", inline labeling option
  available, no task section until/unless a task gets linked.
- Auto-stop path must populate Results identically to manual stop
  (`isAutoStopped: true` still needs to flow into the upgrade-prompt
  copy/condition, matching `ActivityRewardScreen`'s existing behavior).
- Labeling in-place that links a task mid-Results: task-summary section
  must appear reactively, and `useTasks` data must be fresh enough to find
  the newly linked task (may need a refetch/invalidation after label
  confirm, similar to how `refreshAfterActivityChange` works elsewhere).
- Toggling task complete/undo from Results, then exiting to Input, then
  re-entering Results for the *same* completed activity should not be
  possible since exit is manual and one-way to Input — verify no stale
  `resultsData` lingers into the next activity's start (clear `resultsData`
  on `handleBlankStart`/`handleStartClick` in addition to explicit exit).
- Concurrent flag flip: `results_mode` is read once via `useFeatureFlag` at
  render/stop time; no need for extra synchronization since it's a simple
  boolean read, not a mutation — but verify behavior is sane if the flag
  changes value while a Results screen is already open (unlikely in
  practice; app config is fetched once per session).
- Level-up list rendering when `levelUps` includes duplicate levels or is
  empty — reuse existing `normalizedLevelUps` filtering logic unchanged.
- Premium multiplier math (`xpMultiplier / taskXpMultiplier`) when
  `taskXpMultiplier` is `null`/`0` — reuse existing guarded logic from
  `ActivityRewardScreen` verbatim in the extracted component; don't
  re-derive it.

## 6. Tests

New:
- Unit tests for `RewardBreakdown` (moved/adapted from the relevant
  `ActivityRewardScreen.test.tsx` cases: duration formats n/a here since
  that's timer-panel-level, but multiplier breakdown, level-ups, total XP
  row formatting stay).
- Unit tests for `TimerResultsPanel`: renders with/without task, renders
  with/without activity name, debounced relabel triggers update ~1s after
  last keystroke (fake timers), upgrade prompt shown/hidden per
  premium/auto-stop conditions, complete/undo toggle behavior (mirroring
  `ActivityRewardScreen.test.tsx`'s task-toggle coverage), manual-only exit
  (no countdown present at all — assert absence).
- `useActivityInput.test.ts` additions: with `results_mode` on, manual stop
  sets `resultsData` and does not dispatch `OPEN_ACTIVITY_REWARD`; with flag
  off, unchanged (dispatches as today); same for auto-stop path; exiting
  Results clears state and returns to Input.
- `UnifiedTimerHome.test.tsx` additions: Results panel renders instead of
  timer body when `resultsData` present; `SupportFlowModal` still renders
  for flag-off stop.
- Playwright: extend `unified-timer-home.spec.ts` (or add a sibling spec)
  with `results_mode: true` in `stabilizeTimerPage`, covering stop → Results
  → label in place → task summary appears → exit → back to Input.
- a11y: extend `tests/a11y/home-page.spec.ts` / `components.spec.ts` to
  cover the new Results panel markup (focus management on entry/exit,
  labeled controls).

Existing tests to verify unchanged:
- `ActivityRewardScreen.test.tsx` — should pass with only import/shape
  changes from the extraction, no behavior change.
- `SupportFlowModal.test.tsx`, `useSupportFlow.test.tsx`,
  `supportFlowReducer` behavior — untouched for flag-off path.
- `useFeatureFlag.test.ts` — extend/confirm pattern works for the new key
  (likely just needs the new key added to any exhaustive-key type tests).

## 7. Risks

- Extracting `RewardBreakdown` while accidentally changing the premium
  multiplier math or `hasRewardBreakdown` gating condition — copy the
  guard logic exactly, don't "simplify" it during extraction.
- Duplicating (rather than sharing) the upgrade-prompt condition between
  `ActivityRewardScreen` and `TimerResultsPanel` and letting them drift —
  worth a shared tiny pure function even if the containing components
  differ.
- Forgetting to clear `resultsData` on a fresh activity start, causing a
  stale Results screen to flash or stacking state incorrectly.
- Styling regression: `ActivityRewardScreen` currently gets its width
  constraint from the Modal wrapper, not its own CSS — extraction must not
  silently lose that constraint for the modal path, and `TimerResultsPanel`
  needs its own explicit width handling since it has no modal wrapper.
- Missing the auto-stop call site (`useAutoStopCompletionEffect`) when
  wiring the flag branch — both stop paths must be updated together or
  auto-stop will silently keep opening the SupportFlow modal even with the
  flag on.
- Debounce timing drift: reuse a tested debounce utility rather than
  hand-rolling `setTimeout` logic inline, to avoid flaky behavior under
  fast typing/backspacing.

## 8. Open questions

- Exact component/file names (`RewardBreakdown`, `TimerResultsPanel`) — pick
  final names during implementation; not architecturally significant.
- Should the upgrade-prompt condition/copy be factored into one shared pure
  helper now, or left duplicated until a second consumer makes the
  duplication actually annoying? Leaning toward: extract only if it turns
  out to be more than a couple lines of duplicated logic.
- Is there an existing debounce hook/utility in the codebase to reuse for
  the ~1s live relabel, or does this introduce the first one? Needs a check
  during implementation (not surfaced by the initial exploration).
- ~~Does "inline option to label the activity" reuse the exact same
  input/autocomplete component used in the Input state, or a simplified
  text-only field?~~ **Resolved:** reuse `EntitySearchInput` directly, in
  its default (non-`alwaysOpen`) config — that's the absolutely-positioned
  overlay dropdown (`EntitySearchInput.module.scss:35-48`, `z-index:
  $z-index-tooltip`, box-shadow), which is exactly the "renders over other
  content" behavior wanted here, and needs no new component. Note:
  `UnifiedTimerHome.tsx:170-181` deliberately switched its *own* label input
  to `alwaysOpen` (in-flow, no overlay) because the floating dropdown bled
  outside the wrapper card and overlapped the support button below it —
  same class of layout risk applies to `TimerResultsPanel`, which also has
  content below the input (task summary, upgrade prompt, exit button).
  Implementation should verify the panel's overflow/z-index stacking
  handles the overlay cleanly before assuming it's a drop-in; if it bleeds
  the same way, falling back to `alwaysOpen` there too is the proven
  escape hatch.
