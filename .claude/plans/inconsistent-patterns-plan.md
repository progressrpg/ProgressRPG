# Inconsistent Patterns Fixes (Audit §5)

Plan-only. Covers the `blocks`/`slows` findings from
`docs/design-notes/codebase-re-entry-audit.md` §5 ("Inconsistent
patterns"), scoped per your decisions below. The `minor` finding
(`AnnouncementQuerySet.as_manager()` vs `Manager.from_queryset()`
subclass) is excluded per your request.

## Scope decisions (confirmed with you)

| Finding | Severity | Disposition |
|---|---|---|
| Two `get_xp_reward_summary()` implementations | blocks | Already fixed in #829 (commit 4, `points.build_reward_summary`) — not in this plan. |
| Two movement-deciding systems (`commute_tick` vs sun-phase) | blocks | **Document only.** Confirmed via `progress_rpg/celery.py` that only `commute_tick` is on the beat schedule — `move_characters_tick` and `precompute_sun_times`/`schedule_sun_phase_tasks` are commented out, so the sun-phase → `go_home`/`go_outside` path is currently unreachable, not a live parallel system. This plan documents that and flags the sun-phase path as a §7 dead-code candidate; no code removed here. |
| Player-scope `XpModifier` write-only | slows | Already fixed in #833 (commit 1) — not in this plan. |
| Model-delegate vs plain-function service convention | slows | **Skipped.** `check_and_award_daily_goals`/`set_activity_active_modifiers` are cross-model orchestration with no single owning model, unlike `behaviour.generate_day()`; the two conventions are both correct for what they're used for. |
| Four DRF view idioms | slows | **Document only.** Too large/risky to unify in a readability pass; this plan records what differs and why, no view code changes. |
| Frontend `apiFetch` bypasses | slows | **Fixed.** Five new `api/*.ts` modules, one per resource, matching the existing convention (`tasks.ts`, `notes.ts`, ...). |

## 1. High-level strategy

Two commits with an actual code change, plus one documentation-only
commit, ordered safest-first:

1. Add a short note to the audit doc (or a design note) recording the
   `commute_tick`-is-live / sun-phase-is-dead finding and the four view
   idioms, so both are captured without a code change.
2. Extract the frontend `apiFetch` call sites in `useActivityTimer.ts`,
   `useBootstrapGameData.ts`, `useOnboarding.ts`, `useTutorialSteps.ts`,
   `useMaintenanceStatus.ts`, and `TutorialModal.tsx` into five new
   `api/*.ts` modules, updating each caller to import from the new module
   instead of calling `apiFetch` directly.

Note: the audit's file list for this finding also includes
`components/MaintenanceWatcher.tsx`. Checked it directly —
it doesn't call `apiFetch` at all; it registers global
`setMaintenanceHandler`/`setNetworkErrorHandler` callbacks that the
shared `apiFetch` in `utils/api.ts` invokes on 503/network-error. That's
configuring the shared layer's error handling, not bypassing it — not a
real instance of this finding, so it's excluded from commit 2 rather than
silently dropped. Worth a one-line correction note in the PR description
since it's a factual correction to the audit doc's own file list.

## 2. Files likely to change

- `docs/design-notes/codebase-re-entry-audit.md` — add a short
  "Resolved"/"Deferred" annotation to the two `document only` findings,
  following the pattern already used elsewhere in the doc for resolved
  open questions (exists).
- `frontend/src/api/activityTimers.ts` — **new**, wraps
  `set_activity/`, `label_activity/`, `start/`, `reset/`, `complete/`.
- `frontend/src/api/gameData.ts` — **new**, wraps `fetch_info/`
  (bootstrap payload).
- `frontend/src/api/onboarding.ts` — **new**, wraps
  `me/complete_onboarding/`.
- `frontend/src/api/tutorial.ts` — **new**, wraps `tutorial-steps/` and
  `me/mark_tutorial_steps_seen/` (both tutorial-resource endpoints,
  currently split across `useTutorialSteps.ts` and `TutorialModal.tsx`).
- `frontend/src/api/maintenance.ts` — **new**, wraps
  `maintenance_status/`.
- `frontend/src/hooks/useActivityTimer.ts`,
  `useBootstrapGameData.ts`, `useOnboarding.ts`, `useTutorialSteps.ts`,
  `useMaintenanceStatus.ts`,
  `frontend/src/components/TutorialModal/TutorialModal.tsx` — replace
  direct `apiFetch` calls with the new module functions (all exist).
- `frontend/src/api/activityTimers.test.ts`,
  `gameData.test.ts`, `onboarding.test.ts`, `tutorial.test.ts`,
  `maintenance.test.ts` — **new**, mirroring `tasks.test.ts`'s
  mock-`apiFetch` pattern.

## 3. Implementation plan

**Commit 1 — document the two "document only" findings**
- Add a short paragraph under §5's movement-systems row (or as a new
  "Resolved during review"-style note, matching the doc's existing
  convention) stating: `commute_tick` is the only scheduled movement
  trigger; the sun-phase path is unreachable and is a §7 dead-code
  candidate, not addressed here.
- Add an equivalent short note for the four view idioms: name the four
  patterns (`APIView`+`ViewSet`+`@action` in `api/`;
  `ModelViewSet`+queryset mixins in `progression/`; bare `APIView`+
  `ReadOnlyModelViewSet` in `locations/`; `ViewSet`+`@action` in
  `gameplay/`) and record the decision that unifying them is out of
  scope for this readability pass given the size/risk of touching
  permission and queryset scoping across four apps.
- No code change, no tests.

**Commit 2 — frontend API layer extraction**
- `api/activityTimers.ts`: `setActivity(params)`, `labelActivity(name,
  taskId)`, `startTimer()`, `resetTimer()`, `completeTimer(activityName,
  elapsedSeconds, source)` — signatures derived from each call site's
  existing body payload; keep the same endpoint paths and payload shapes
  exactly (no request/response format changes).
- `api/gameData.ts`: `fetchInfo(): Promise<FetchInfoResponse>`.
- `api/onboarding.ts`: `completeOnboarding(): Promise<void>`.
- `api/tutorial.ts`: `fetchTutorialSteps()`, `markTutorialStepsSeen(stepIds:
  number[])`.
- `api/maintenance.ts`: `fetchMaintenanceStatus():
  Promise<MaintenanceStatusApiResponse>`.
- Update each of the six call sites to import from its new module and
  drop the direct `apiFetch` import (unless the file also uses `apiFetch`
  for something not covered by these five modules — check each file at
  implementation time).
- One commit for all five files/call-site updates — mechanical, same
  pattern repeated five times, low value in splitting further.

## 4. Design decisions

- **One file per resource, not per hook**: matches your answer and the
  existing convention (`tasks.ts` serves multiple hooks/components; a new
  `api/tutorial.ts` similarly serves both `useTutorialSteps.ts` and
  `TutorialModal.tsx` rather than one file per caller).
- **Excluding `MaintenanceWatcher.tsx`**: it doesn't call `apiFetch`, so
  including it in the "fix" would be non-mechanical guesswork about what
  a fix would even mean. Treated as a correction to the audit's finding,
  not a silent scope cut.
- **Doc-only commit lives in the audit doc itself, not a new file**: the
  doc already has a "Resolved during review" precedent (see #828's PR
  body) for recording decisions inline rather than spawning a new
  document — reuses that convention instead of introducing a new one.
- **No `api/onboarding.ts`/`api/tutorial.ts` merge**: onboarding and
  tutorial are adjacent but distinct resources (`/me/complete_onboarding/`
  vs `/tutorial-steps/` + `/me/mark_tutorial_steps_seen/`) with no shared
  types; kept separate to match the one-file-per-resource convention
  rather than one-file-per-adjacent-feature.

## 5. Edge cases

- **Commit 1**: none — documentation only.
- **Commit 2**: `useActivityTimer.ts`'s commented-out `reset()` call
  (line ~350) — leave the comment as-is, don't uncomment or delete it as
  part of this extraction (out of scope, unrelated to the bypass finding).
  Verify no caller relies on `apiFetch`'s specific error-throwing
  behavior in a way the wrapper function needs to preserve explicitly
  (it will, by construction, since the wrapper just calls `apiFetch`
  internally — same promise chain, same thrown errors).

## 6. Tests

- **Commit 1**: none.
- **Commit 2**: new `*.test.ts` per new module, mocking `apiFetch` the
  same way `api/tasks.test.ts` does — asserting each wrapper calls
  `apiFetch` with the expected path/method/body. Existing hook-level
  tests (if any exist for `useActivityTimer`, `useOnboarding`, etc.)
  continue to pass unmodified since the wrapper preserves the exact same
  request shape and return value.

## 7. Risks

- Commit 2: missing a payload field or mis-transcribing a body shape
  while extracting `useActivityTimer.ts`'s five calls (it has the most
  call sites and the most parameters) — diff each wrapper function
  against the original inline `apiFetch` call carefully rather than
  rewriting from memory.
- Commit 2: `useMaintenanceStatus.ts` and `MaintenanceWatcher.tsx` are
  easy to conflate since both are "maintenance"-named — confirm at
  implementation time that only `useMaintenanceStatus.ts` gets touched.
- Commit 1: the audit doc is actively being annotated by multiple
  in-flight sibling PRs (#835, #836, #837, #838) — check for merge
  conflicts against those before finalizing wording, since more than one
  branch touches this same file's §-level content.

## 8. Open questions

- None outstanding — all four ambiguous findings were resolved via your
  answers above.
