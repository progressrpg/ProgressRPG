# Test Coverage as Documentation (Audit §6)

Plan-only. Covers the `blocks`/`slows` findings from
`docs/design-notes/codebase-re-entry-audit.md` §6 ("Test coverage as
documentation").

Two of the three `blocks` findings, and one `slows` finding, are already
resolved — checked directly rather than trusting the audit doc, since it
predates some of this session's PRs:

- **`gameplay/utils.py` (`control_timers`/`process_initiation`/
  `process_completion`)** (`blocks`, `[PCL path]`) — already covered.
  `origin/claude/readability-top-five` (#829) added
  `gameplay/tests/test_utils.py` with `ControlTimersTests`,
  `ProcessInitiationTests`, `ProcessCompletionTests` directly exercising
  all three.
- **`step_toward`'s distance-budget loop** (`blocks`) — already covered.
  #829 added `locations/tests/test_movement.py` covering multi-segment
  budget spend, mid-segment stops, speed scaling, exact arrival, and the
  no-active-journey/completed-journey paths.
- **`get_productivity`** (`slows`) — already covered. `test_ap.py` (on
  the current `#828` branch itself, predating this plan) has a full
  `GetProductivityTests` class. The audit finding is stale.

This plan covers what's left: `behaviour_services.py`'s `sync_to_now`/
`advance`/`interrupt_current_activity` (`blocks`), and `find_path` /
`go_home`/`go_outside` (`slows`).

## 1. High-level strategy

Two independent test-only commits, no production code changes:

1. `character/services/behaviour_services.py` — `sync_to_now`, `advance`,
   `interrupt_current_activity`.
2. `locations/services/movement.py` — `find_path`, `go_home`,
   `go_outside`.

Both add to existing test files/classes rather than creating new ones,
following each app's established per-module test-file convention
(`test_behaviour_services.py`, and `test_movement.py` once #829 lands —
see Design decisions for what to do if this PR merges first).

## 2. Files likely to change

- `character/tests/test_behaviour_services.py` — add
  `SyncToNowTests`, `AdvanceTests`, `InterruptCurrentActivityTests`
  classes, following the existing `WorkActivitiesForTests`/
  `GenerateDayWorkActivityTests`/`DeleteDayTests` class-per-function
  convention already in the file (exists).
- `locations/tests/test_movement.py` — add `FindPathTests`,
  `GoHomeTests`, `GoOutsideTests`. **Does not exist on this branch** (only
  added in #829, not yet merged into `development`) — see Design
  decisions for the sequencing implication.

## 3. Implementation plan

**Commit 1 — `behaviour_services.py` coverage**
- `SyncToNowTests`: current activity with `started_at` already set (no-op
  return); current activity with `started_at is None` (gets backfilled to
  `scheduled_start`); no current activity, one upcoming (`returns
  upcoming`); no current, no upcoming (`returns None`); an ended-but-
  incomplete activity in the window gets `complete_past()`'d before the
  current-activity lookup runs.
- `AdvanceTests`: a `current` activity in-window gets force-completed via
  `complete_now()`, and the next activity's `started_at` is backfilled
  when its `scheduled_start <= now`; no `current` in-window falls through
  to `sync_to_now`; no `next` activity after the current one completes
  (returns `None`).
- `InterruptCurrentActivityTests`: an active current activity is split —
  the original is `complete_now()`'d and a new `CharacterActivity` is
  created starting `now` with the same `scheduled_end`; no current
  activity returns `None`; an already-complete current activity returns
  `None` without creating anything.
- Reuse the existing `CharacterActivity`/`Behaviour` factory setup already
  present in `GenerateDayWorkActivityTests`/`DeleteDayTests` rather than
  inventing new fixture helpers.

**Commit 2 — `movement.py` coverage**
- `FindPathTests`: confirmed as "very dumb" in its own docstring/comment
  — pin actual current behavior (single-hop direct connection, and
  whatever it does for a discononnected/no-path case) rather than
  asserting an idealized shortest-path guarantee it doesn't provide. The
  point of this test is to document what it actually does, per the
  audit's framing of this whole section.
- `GoHomeTests`: character with a home building sets destination there
  (via `set_destination`, verifiable through `is_moving`/`target_node`
  becoming set, matching the assertion style already used for movement
  state elsewhere in `locations/tests/`); character with no home is a
  no-op (matches the existing `print(...)` early-return branches — assert
  no destination/journey created, not the print output).
  `current_node_id == destination_node.id` is a no-op.
  Random-node home model
  vs single fixed building at implementation time — read the model
  currently to confirm `home` is a single node/building, not itself
  randomized.
- `GoOutsideTests`: destination lands within `radius` of the character's
  current location (via `pick_random_outside_node`/
  `get_nearby_outside_nodes`); no nearby outside node found is a no-op
  (mirrors `go_home`'s no-home no-op).

## 4. Design decisions

- **Test file for movement.py — sequencing with #829**: #829 (not yet
  merged) introduces `locations/tests/test_movement.py` for
  `step_toward`. This plan's commit 2 should target that same file to
  keep movement.py's tests in one place, per the precedent #829 itself
  establishes ("following the precedent of test_wander.py covering
  services/wander.py"). Two orderings are possible depending on merge
  order: if #829 merges into `development` before this plan is
  implemented, add to the file it created; if this plan's branch is
  implemented first (independently, since PR #839's stack doesn't
  include #829's commits), create `locations/tests/test_movement.py`
  fresh with just `find_path`/`go_home`/`go_outside`, and expect a merge
  conflict/duplicate-file resolution against #829 when both eventually
  reach `development` — flagged as a risk below rather than solved here,
  since it depends on merge order neither plan controls.
- **No test added for `find_path` beyond pinning current behavior**: the
  function is self-documented as "very dumb" — the audit's own framing is
  that a reader needs to know *what it actually does*, not that it needs
  to be improved into a real shortest-path algorithm. Alternative
  considered: also fix `find_path` to be a real pathfinder — rejected,
  out of scope for a test-coverage finding and a behavior change nothing
  asked for.
- **Reusing existing fixture patterns over new factories**: both new test
  classes extend files that already have working
  `Character`/`Behaviour`/`CharacterActivity` setup — reuse over
  introducing `factory_boy` factories or similar, consistent with the
  planning template's reuse principle.

## 5. Edge cases

- `interrupt_current_activity`'s `boost_ended` parameter is accepted but
  never read inside the function body (checked: it's dead-parameter,
  unused in the current implementation) — worth a test asserting the
  function behaves identically regardless of that argument's value, which
  documents the parameter's current no-op status rather than silently
  ignoring it. Not a fix — just pinning what's there, consistent with
  this section's "documentation" framing.
- `sync_to_now`/`advance` both use `select_for_update()` inside
  `transaction.atomic` — tests need `TestCase` (transactional), not
  `SimpleTestCase`, matching the existing file's use of `TestCase`.

## 6. Tests

This plan *is* the tests — see Implementation plan above for exact
coverage. No existing tests need modification; these are additive-only
files/classes.

## 7. Risks

- Commit 2: potential duplicate-file conflict with #829's
  `test_movement.py` depending on merge order — see Design decisions.
  Worth flagging to whoever merges these that the two PRs should be
  coordinated (either rebase this one onto #829's branch before
  implementing, or resolve the conflict at merge time).
- Commit 1: `interrupt_current_activity`'s creation of a new
  `CharacterActivity` mid-activity needs a correct `scheduled_end` copy —
  easy to assert the wrong field (`activity.scheduled_end` before vs.
  after `complete_now()` may differ if `complete_now()` mutates it) —
  verify field values at implementation time by reading `complete_now()`.
- Both commits: since this session can't run the Django test suite
  (no Docker/Postgres/GDAL in this environment), these tests are
  unverified until run locally — flag this the same way #829/#833 did.

## 8. Open questions

- None outstanding.
