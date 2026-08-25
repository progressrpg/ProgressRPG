# Naming Clarity Fixes (Audit §2)

Plan-only. Covers the `blocks`/`slows` findings from
`docs/design-notes/codebase-re-entry-audit.md` §2 ("Naming clarity"). The
two `minor` findings (`get_elapsed_time`/`compute_elapsed`/`apply_elapsed`
near-synonyms; empty `CharacterManager`) are out of scope per your request.

One finding in this section — `process_initiation`/`process_completion`
(`gameplay/utils.py:144,177`) — is already planned as commit 8 of
`.claude/plans/working-memory-load-plan.md` (PR #835), folded in there at
your request even though it's technically a §2 finding. Not repeated here
to avoid two plans touching the same rename.

## 1. High-level strategy

Three independent, mechanical renames/clarifications, each scoped to one
module and its call sites. None change behavior. Ordered safest-first:

1. Rename `end_online_boost` → a name that covers both modifier kinds it
   actually ends (`blocks` severity — the name is actively misleading about
   a side effect).
2. Disambiguate `progression/ap.py` vs `progression/points.py` (`slows`).
3. Rename `movable` → `character` throughout `locations/services/movement.py`
   (`slows`).

Each is its own commit; commits are independently revertable and don't
depend on each other.

## 2. Files likely to change

- `gameplay/tasks.py` — rename `end_online_boost` (exists).
- `gameplay/services/xp_modifiers.py` — update `task=end_online_boost`
  default/import (exists).
- `gameplay/tests/test_xp_modifiers.py` — update patched name (exists).
- `progression/ap.py`, `progression/points.py` — docstring-only
  clarification, no rename (exist).
- `locations/services/movement.py` — rename `movable` parameter
  throughout (exists).
- `locations/models.py` — no signature change needed; call sites pass
  positionally/by the same keyword names already (`node=`, `obj=`,
  `point=`) except the `movable` positional itself, which is unaffected
  since callers pass `self` positionally.
- No new files.

## 3. Implementation plan

**Commit 1 — rename `end_online_boost`**
- Rename the Celery task in `gameplay/tasks.py:216` to `end_xp_modifier`
  (it ends any `XpModifier` — online boost or activity-active — and its
  `interrupt_current_activity()` side effect fires for both; the current
  name only describes the online-boost case).
- Update the import and `task=` default in
  `gameplay/services/xp_modifiers.py` (both the `from gameplay.tasks
  import end_online_boost` and `schedule_modifier_end`'s
  `task=end_online_boost` default).
- Update the three `mock.patch.object(xpm.end_online_boost, ...)` /
  equivalent references in `gameplay/tests/test_xp_modifiers.py`.
- No migration — it's a Python-level task function name, not a
  `task_name` string stored anywhere (confirm no `task_id` string match
  relies on the dotted path — `task_id` is Celery's own generated result
  ID, not the task's importable name, so this is safe).

**Commit 2 — disambiguate `ap.py` vs `points.py`**
- No rename: both names are load-bearing enough elsewhere (`ap.py`'s
  Phase-1 migration docstring references `progression-track-abstraction.md`;
  `points.py` is referenced by docstring/help_text in `progression/models.py`
  and `core/models.py`). Renaming either risks more churn than the finding
  warrants for a `slows`, not a `blocks`.
- Instead, add a one-line cross-reference to the top of each module's
  docstring stating what the *other* module owns, so a reader who opens
  the wrong one is redirected immediately:
  - `ap.py`: owns the level/AP curve (`threshold_for_level`, `apply_xp`,
    `total_ap_earned`) and the online/activity-boost multiplier lookup
    (`get_multiplier`, `get_productivity`).
  - `points.py`: owns the skill-XP base rate and mastery multiplier
    (`base_rate`, `xp_for_duration`, `xp_mastery_multiplier`) used for
    per-skill XP and the AP mastery bonus.
- This is documentation, not code — no call sites change.

**Commit 3 — rename `movable` → `character` in `movement.py`**
- `Movable` (the mixin, `locations/models.py:26`) has exactly one
  subclass, `Character` (`character/models/character.py:340`); every
  caller of every function in `movement.py` passes a `Character`
  (confirmed: `Movable`'s own methods pass `self`, and there are no other
  external callers of the module). The generic `movable` parameter name
  implies polymorphism that doesn't exist.
- Rename the parameter in all ~10 module-level functions in
  `locations/services/movement.py` (`go_home`, `get_nearby_outside_nodes`,
  `pick_random_outside_node`, `go_outside`, `set_destination`,
  `step_toward`, `arrive`, plus internal uses) from `movable` to
  `character`. `find_path` is unaffected (takes `start_node`/`end_node`,
  not a movable).
- No call-site changes needed beyond the module itself: `Movable`'s
  wrapper methods (`locations/models.py:70-83`) call
  `movement_service.go_home(self)` etc. positionally, so only the callee's
  parameter name changes.
- Leave the `Movable` mixin/class name itself alone — the audit finding is
  about the function parameter, not the class, and the class name is
  reasonable as a general "has a location and can move" abstraction even
  with one current subclass.

## 4. Design decisions

- **`end_online_boost` → `end_xp_modifier`, not something more specific
  per-scope**: the task already branches on nothing scope-specific — it
  unconditionally deactivates the modifier and interrupts the current
  activity. A name naming both scopes it can end (`end_online_or_activity_boost`)
  is more accurate but longer without adding clarity; `end_xp_modifier`
  matches the model it operates on (`XpModifier`) and drops the
  boost-specific claim entirely. Alternative considered: keep the name,
  add a docstring — rejected because the audit flags this as `blocks`
  severity specifically because the *name* is misleading, not because
  the behavior is undocumented.
- **Docstring cross-reference over renaming `ap.py`/`points.py`**:
  renaming either risks breaking the Phase-1 migration story documented in
  `ap.py`'s own docstring (it's deliberately named to eventually host a
  `ProgressionTrack` model per `.claude/plans/progression-track-abstraction.md`).
  A `slows` finding doesn't justify unwinding that. Alternative considered:
  merge the two modules — rejected, they have genuinely different
  responsibilities (level curve vs. skill-XP rate) and merging would
  recreate the "two things in one file" problem elsewhere in the audit.
- **`movable` → `character`, not leaving it generic**: the audit's
  complaint is specifically that genericity is unearned. Renaming to the
  concrete type matches the repo's existing convention elsewhere (e.g.
  `Journey.character`, `ActivityTimer.player`) of naming parameters after
  what they actually are, not a hypothetical abstraction.

## 5. Edge cases

- **Commit 1**: any Celery worker mid-flight with an already-scheduled
  `end_online_boost` task at deploy time would reference the old task
  name by dotted path (Celery serializes tasks by registered name, which
  defaults to `module.function`). A rename changes the registered task
  name, so an in-flight scheduled task from before deploy would fail to
  route after deploy. Given `schedule_modifier_end` schedules with `eta=`
  typically minutes out (grace window is 5 minutes per
  `ACTIVITY_ACTIVE_GRACE_MINUTES`), this is a narrow window — flagged as
  a deploy-sequencing risk, not a blocker.
- **Commit 2**: none — docstring-only.
- **Commit 3**: none — parameter rename only, no behavior change, no
  external callers pass by keyword `movable=`.

## 6. Tests

- **Commit 1**: update existing patch targets in
  `gameplay/tests/test_xp_modifiers.py` (4 occurrences) to the new name;
  no new test needed, existing coverage of `schedule_modifier_end` /
  modifier-end behavior already exercises this path.
- **Commit 2**: none — no behavior change.
- **Commit 3**: none — no behavior change. Existing movement coverage
  (`locations/tests/test_wander.py`, `test_schedule.py`, `test_models.py`,
  `test_character_serializers.py`) continues to pass unmodified since none
  call `movement.py` functions with `movable=` as a keyword.

## 7. Risks

- Missing one of the 4 `end_online_boost` references in
  `test_xp_modifiers.py` (grep confirmed exactly 4: 3 test patches +
  1 import) — a stale patch target would silently patch nothing and the
  test would call the real Celery task.
- Commit 1's deploy-sequencing edge case above — worth a one-line note in
  the PR description so whoever deploys it is aware, not a code change.
- Commit 3 touching a function used inside a DB transaction
  (`set_destination`) — pure rename, but worth double-checking the diff
  doesn't accidentally touch the `transaction.atomic()` block's logic.

## 8. Open questions

- None outstanding — all three items are confirmed mechanical from
  reading the actual call sites.
