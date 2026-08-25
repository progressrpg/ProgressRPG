# Readability audit — top five remediations

Source: `docs/design-notes/codebase-re-entry-audit.md`. Five highest-impact
items, scoped so that **none of them changes observable behaviour** — that is
what makes them cheap to review and safe to land in any order after the first
two.

Items, in implementation order:

1. Tests for `gameplay/utils.py` timer-control functions
2. `control_timers` unbound-variable bug (`gameplay/utils.py:120-124`)
3. `Timer` status literals → `TextChoices`
4. The two divergent `get_xp_reward_summary()` implementations
5. `step_toward`'s missing test (`locations/services/movement.py:152-205`)

**Moved out of this plan:** modifier stacking (originally item 3) is now
`.claude/plans/modifier-stacking-plan.md`. It was scoped as a comment-only
change on the assumption that the current single-product rule was staying. It
isn't — mixed additive/multiplicative stacking is planned — so it became a
model field, a migration and a rewrite of `get_multiplier`. That is a behaviour
change and does not belong beside four no-op changes.

---

## 1. High-level strategy

Four mechanical changes plus one design decision.

Items 1–2 are one unit: a real bug on the PlayerCharacterLink path being
re-enabled, and the tests that should have caught it. They go first and
together — fixing the bug without the tests leaves the next regression equally
invisible.

Items 3–5 are independent of each other and of 1–2. Item 3 is mechanical but
wide (41 non-test call sites); it goes after the tests exist so the sweep has
something to fail against. Item 4 is the only one needing a design decision.
Item 5 closes the most consequential remaining test gap.

Nothing here introduces a new module, service or abstraction. Every change
extends something that already exists.

---

## 2. Files likely to change

All files already exist; no new source files are required. Two new test files.

**Items 1–2**
- `gameplay/tests/test_utils.py` — **new**. No test module currently covers
  `gameplay/utils.py`; `test_disconnect_grace.py` only patches `control_timers`
  out.
- `gameplay/utils.py` — the `control_timers` mode dispatch.

**Item 3**
- `gameplay/models.py` — `Timer.STATUS_CHOICES` → nested `TextChoices`.
- `gameplay/views.py`, `gameplay/tasks.py`, `gameplay/consumers.py`,
  `api/views.py` — literal call sites.
- `gameplay/migrations/` — **new** auto-generated `AlterField` (choices-only).
- `frontend/src/types/enums.ts` — `TimerStatus` already mirrors the backend;
  verify parity, add a pointer comment. No behavioural change.

**Item 4**
- `progression/models.py` — both `get_xp_reward_summary()` implementations.
- `progression/points.py` — shared summary-shaping helper (extends an existing
  module rather than adding one).

**Item 5**
- `locations/tests/test_movement.py` — **new**, or extend
  `locations/tests/test_models.py` if that is where movement coverage is
  expected to live.

---

## 3. Implementation plan

Six commits, each independently reviewable and revertable.

### Commit 1 — test `gameplay/utils.py` as-is
Add `gameplay/tests/test_utils.py` covering current behaviour of
`start_server_timers`, `pause_server_timers` and `control_timers`, including a
test asserting what an unrecognised mode currently does. Written first, so the
bug is demonstrated before it is fixed. Follow existing `gameplay/tests/`
conventions (the `_linked_player_and_character()`-style helpers in
`test_xp_modifiers.py`).

### Commit 2 — fix the invalid-mode branch
Make `control_timers` return `False` for an unrecognised mode instead of
falling through to an unassigned `server_success`. Flip the commit-1 assertion.
Two commits rather than one so the fix is reviewable against a failing test.

### Commit 3 — `Timer` status as `TextChoices`
Replace `STATUS_CHOICES` with a nested `TextChoices` on `Timer`, keeping every
stored value byte-identical. Sweep the 41 non-test literal sites. Generate the
`AlterField` migration (choices metadata only — no data migration, no column
change). Leave the 47 test-file literals alone: they are assertions about the
wire/DB value, and a test hardcoding `"active"` is doing its job. Add the
frontend parity comment in `enums.ts`.

### Commit 4 — align the two reward summaries
Per §4, the narrow version: extract shared dict-shaping into
`progression/points.py`, have both call sites use it, document the divergence
at both. No key renames, no behaviour change.

### Commit 5 — test `step_toward`
Cover the distance-budget loop: a tick crossing several short segments in one
budget, a tick ending mid-segment, and arrival. This is the logic the frontend
walker animation must agree with, and `test_models.py:173` currently only
asserts it "does not raise".

---

## 4. Design decisions

### Item 3: nested `TextChoices` vs a module-level enum
**Chosen:** a `TextChoices` nested on `Timer`, mirroring
`ActivityDefinition.Kind`, `Node.Kind`, `CharacterLocation.Role` and
`Character.SexChoices` — the established convention in this codebase.
**Alternative:** a module-level `TimerStatus` enum, importable without pulling
in the model. Rejected: nothing outside `gameplay` and `api` needs the values,
and it would break with every other choices enum in the project.
**Why:** consistency is the whole point of the change; a new idiom would add a
sixth thing to relearn.

### Item 3: leave `Journey.status` alone
The audit flagged `locations/models.py:296` as the same class of problem.
**Deliberately out of scope.** It carries a data question — `place_characters.py:112`
writes a `"cancelled"` value that neither `is_complete` nor the unique
constraint recognises — and answering it is not a readability change. Bundling
would turn a mechanical sweep into a behavioural one.

### Item 4: shared shaping helper vs full unification vs docstrings only
**Chosen:** extract only the common dict construction (`_fmt`, the key set, the
`duration_seconds`/`base_xp`/`xp_gained` fields) into `progression/points.py`,
which already owns the shared formula. Each model keeps its own multiplier
composition and passes its components in.
**Alternative A — full unification** into one function taking named
multipliers. Rejected: the two genuinely differ (player is premium × task ×
mastery; character is kind × boost × mastery), and collapsing them needs a
flags-or-kwargs parameter harder to read than the two current functions.
**Alternative B — docstrings only.** Rejected as insufficient: it documents the
drift without stopping the next key from diverging.
**Why:** the finding was "two implementations, different key sets, no statement
of which rules apply where". The helper fixes the key set; the docstrings fix
the statement. Neither touches the multiplier logic, which is where the risk is.

### Item 4: additive only — no key renames
`reward_breakdown` is a persisted `JSONField` (`progression/models.py:421`),
exposed via `progression/serializers.py:87,307`, and the frontend reads
`base_xp` / `xp_multiplier` / `task_xp_multiplier` at
`useActivityTimer.ts:373-375` and `useActivityInput.ts:62-65`. Renaming a key
would silently break historical rows, which are never backfilled by design.
Any key alignment must add, never rename or remove.

**Coordination note:** the modifier-stacking plan's commit 5 also adds keys to
`CharacterActivity.get_xp_reward_summary`. Whichever lands second should rebase
onto the other rather than both editing that dict independently.

---

## 5. Edge cases

**Items 1–2.** `control_timers` is `async` and calls `database_sync_to_async`;
the new tests need `TransactionTestCase` or `async_to_sync` wrapping, matching
`test_consumers.py`. `send_group_message` needs the in-memory channel layer,
not a live Redis.

**Item 3.**
- Values built from a variable rather than a literal (e.g. `f"skipped:{timer.status}"`
  at `gameplay/tasks.py:88`) are unaffected and must not be "fixed".
- `status__in=[...]` querysets and `Q(status="active")` at `gameplay/tasks.py:136`
  must keep identical values — a typo silently changes a sweep's scope rather
  than erroring.
- `max_length=20` stays; no value grows.
- Confirm `makemigrations` produces exactly one `AlterField` and no column
  alteration before committing.

**Item 4.**
- `PlayerActivity.get_xp_reward_summary` takes a `duration` override (used by
  offline logging at `progression/services.py:99`); `CharacterActivity`'s does
  not. The helper must not assume one signature.
- `_fmt` returns `int` or `float` depending on integrality — moving it must
  preserve that exactly, since the values land in stored JSON and in frontend
  number formatting.

**Item 5.** `step_toward` mutates `movable` in place and is called inside
`move_characters_tick`'s `bulk_update` batching; tests should exercise the
function directly rather than through the task, and must set `srid=3857` on
constructed points to match production geometry.

**Concurrency.** None of the five introduces new concurrency. Item 2 touches a
function called from an async consumer, but the fix is a local control-flow
correction with no new shared state. Item 3 changes no write path. No new
locking, transactions or idempotency controls are needed, and adding any would
be unjustified.

---

## 6. Tests

**New — `gameplay/tests/test_utils.py`** (commit 1, the substantive addition):
- `start_server_timers` in each valid status, and in an invalid one.
- `pause_server_timers` for `completed`/`empty` (no-op) vs other statuses.
- `control_timers` with `"start"`, `"pause"`, and an unrecognised mode — the
  last is the regression test for item 2.
- The websocket group message on both success and failure paths; that shape is
  the contract the frontend consumes.
- `process_initiation` / `process_completion` success and failure paths. These
  are on the PlayerCharacterLink path being re-enabled, so they should be
  tested even though they are not currently reachable from the consumer.

**New — `step_toward`** (commit 5): multi-segment budget in one tick;
mid-segment stop; arrival clearing `is_moving`/`target_node`; a journey with no
next node.

**Existing — modify:**
- `test_disconnect_grace.py:275,305,337` patch `control_timers` wholesale. Keep
  the patching, but confirm the mock's call signature still matches after
  item 2.
- After item 3, run the `gameplay` and `api` suites; any failure indicates a
  value changed, which is the one thing the sweep must not do.

**Not needed:** item 4 is a pure refactor. Existing coverage
(`test_premium_activity_rewards.py`, `test_xp_modifiers.py:240-288`,
`test_activity_timer_premium.py`) already pins both summaries' outputs; if those
pass unchanged, the extraction is correct.

Run individual/scoped test units only — full Vitest and Playwright suites are
the user's to run.

---

## 7. Risks

- **Item 3 sweep changes a stored value.** The highest-consequence mistake
  available: a status string differing by a character silently breaks a sweep
  or a queryset with no error. Diff the literal values before/after, not just
  run tests.
- **Item 3 scope creep into `Journey.status`.** It looks like the same change
  and is not. See §4.
- **Item 1 tests written against the buggy behaviour and left that way.** The
  commit-1/commit-2 split exists to prevent this; the assertion must flip.
- **Item 4 treated as licence to unify the multiplier logic.** The reward
  formulas are the most balance-sensitive code in the project. The refactor is
  dict-shaping only.
- **Item 4 renaming a key for tidiness.** Breaks historical `reward_breakdown`
  snapshots. Additive only.
- **Item 2 fixed by making the invalid mode raise.** It is called from an async
  consumer where an exception has a different blast radius than a `False`
  return; match the function's existing failure contract.
- **Item 4 colliding with the modifier-stacking plan** over the same reward
  dict. See the coordination note in §4.

---

## 8. Open questions

1. **Is `Journey.status = "cancelled"`** (`place_characters.py:112`) a real
   third state or a bug? Blocks nothing here — item 3 excludes `Journey` — but
   it determines whether a follow-up plan is needed.
2. **Where should movement tests live?** `locations/tests/test_models.py`
   currently holds the journey/movement coverage despite `step_toward` living
   in `locations/services/movement.py`. Commit 5 should follow whichever
   convention is intended rather than establishing a third.
