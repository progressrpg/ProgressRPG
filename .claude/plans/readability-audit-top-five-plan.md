# Readability audit — top five remediations

Source: re-entry readability audit (2026-08-25). Five highest-impact items,
revised after confirming the PlayerCharacterLink websocket path is in-progress
work being re-enabled, not dead code.

Items, in implementation order:

1. `control_timers` unbound-variable bug (`gameplay/utils.py:120-124`)
2. Tests for `gameplay/utils.py` timer-control functions
3. Modifier stacking/precedence comment (`progression/ap.py:66-81`)
4. `Timer` status literals → `TextChoices`
5. The two divergent `get_xp_reward_summary()` implementations

---

## 1. High-level strategy

Four independent changes plus one design decision, sequenced so the risky work
lands on tested ground.

Items 1–2 are one unit: a real bug on the path being re-enabled, and the tests
that should have caught it. They go first and together — fixing the bug without
the tests leaves the next regression equally invisible.

Item 3 is a comment-only change with no blast radius. It goes early because it's
cheap and because the answer it records is a prerequisite for reasoning about
item 5.

Item 4 is mechanical and wide (41 non-test call sites). It goes after the tests
exist, so the sweep has something to fail against.

Item 5 is the only one needing a design decision, and it interacts with the
in-flight link work. Scoped deliberately narrow — see §4.

Nothing here introduces a new module, service or abstraction. Every change
extends something that already exists.

---

## 2. Files likely to change

All files already exist; no new source files are required. Two new test files.

**Item 1**
- `gameplay/utils.py` — the `control_timers` mode dispatch.

**Item 2**
- `gameplay/tests/test_utils.py` — **new**. No test module currently covers
  `gameplay/utils.py`; `test_disconnect_grace.py` only patches `control_timers`
  out.

**Item 3**
- `progression/ap.py` — docstring/comment on `get_multiplier`.

**Item 4**
- `gameplay/models.py` — `Timer.STATUS_CHOICES` → nested `TextChoices`.
- `gameplay/views.py`, `gameplay/tasks.py`, `gameplay/consumers.py`,
  `api/views.py` — literal call sites.
- `gameplay/migrations/` — **new** auto-generated `AlterField` (choices-only).
- `gameplay/tests/*` — 47 literal occurrences; see §3 for why these are handled
  separately.
- `frontend/src/types/enums.ts` — `TimerStatus` union already mirrors the
  backend; verify parity, add a pointer comment. No behavioural change.

**Item 5**
- `progression/models.py` — both `get_xp_reward_summary()` implementations.
- `progression/points.py` — shared summary-shaping helper (extends an existing
  module rather than adding one).

---

## 3. Implementation plan

Five commits, each independently reviewable and revertable.

### Commit 1 — test `gameplay/utils.py` as-is
Add `gameplay/tests/test_utils.py` covering the current behaviour of
`start_server_timers`, `pause_server_timers` and `control_timers`, including a
test asserting what an unrecognised mode currently does. Written first, so the
bug is demonstrated before it's fixed. Follow the existing `gameplay/tests/`
conventions (`TestCase`, the `_linked_player_and_character()`-style helpers in
`test_xp_modifiers.py`).

### Commit 2 — fix the invalid-mode branch
Make `control_timers` return `False` for an unrecognised mode instead of
falling through to an unassigned `server_success`. Flip the test from commit 1
to assert the corrected behaviour. Two commits rather than one so the fix is
reviewable against a failing test.

### Commit 3 — document modifier stacking
Extend `get_multiplier`'s docstring in `progression/ap.py` to state the
stacking rule (all active modifiers multiply, no cap, no precedence) and
whether that is intended. **Blocked on the open question in §8** — this commit
records a decision, it does not make one.

### Commit 4 — `Timer` status as `TextChoices`
Replace `STATUS_CHOICES` with a nested `TextChoices` on `Timer`, keeping every
stored value byte-identical. Sweep the 41 non-test literal sites. Generate the
`AlterField` migration (choices metadata only — no data migration, no column
change). Leave the 47 test-file literals alone: they are assertions about the
wire/DB value, and a test that hardcodes `"active"` is doing its job. Add the
frontend parity comment in `enums.ts`.

### Commit 5 — align the two reward summaries
Per §4, the narrow version: extract the shared dict-shaping into
`progression/points.py`, have both call sites use it, and document the
divergence at both. No key renames, no behaviour change.

---

## 4. Design decisions

### Item 4: nested `TextChoices` vs a module-level enum
**Chosen:** a `TextChoices` nested on `Timer`, mirroring
`ActivityDefinition.Kind`, `Node.Kind`, `CharacterLocation.Role` and
`Character.SexChoices` — the established convention in this codebase.
**Alternative:** a module-level `TimerStatus` enum in `gameplay/models.py`,
importable without pulling in the model. Rejected: nothing outside `gameplay`
and `api` needs the values, and it would break with every other choices
enum in the project.
**Why:** consistency is the whole point of the change. A new idiom would add a
sixth thing to relearn.

### Item 4: leave `Journey.status` alone
The audit flagged `locations/models.py:296` (`Journey.status`, no choices, plus
a `"cancelled"` value written at `place_characters.py:112` that no reader
recognises) as the same class of problem. **Deliberately out of scope here.**
That one has a genuine data-integrity question attached — is `"cancelled"` a
real third state or a bug? — and answering it is not a readability change.
Bundling them would turn a mechanical sweep into a behavioural one.

### Item 5: shared shaping helper vs full unification vs docstrings only
**Chosen:** extract only the common dict construction (`_fmt`, the key set, the
`duration_seconds`/`base_xp`/`xp_gained` fields) into `progression/points.py`,
which already owns the shared formula. Each model keeps its own multiplier
composition and passes its components in.
**Alternative A — full unification** into one function taking a list of named
multipliers. Rejected: the two genuinely differ (player rewards are premium ×
task × mastery; character rewards are kind × boost × mastery), and collapsing
them would need a flags-or-kwargs parameter that is harder to read than the two
current functions.
**Alternative B — docstrings only**, cross-referencing each other. Rejected as
insufficient: it documents the drift without stopping the next key from
diverging.
**Why:** the audit finding was "two implementations with different key sets and
no statement of which rules apply where". The helper fixes the key set; the
docstrings fix the statement. Neither requires touching the multiplier logic,
which is where the risk lives.

### Item 5: additive only — no key renames
`reward_breakdown` is a persisted `JSONField` on both `TimeRecord` subclasses
(`progression/models.py:421`), exposed via `progression/serializers.py:87,307`,
and the frontend reads `base_xp` / `xp_multiplier` / `task_xp_multiplier` at
`useActivityTimer.ts:373-375` and `useActivityInput.ts:62-65`. Renaming a key
would silently break historical rows, which are never backfilled by design
(rewards are recomputed live, but stored breakdowns are snapshots). Any key
alignment must add, never rename or remove.

---

## 5. Edge cases

**Item 2 (tests).** `control_timers` is `async` and calls
`database_sync_to_async`; the new tests need `TransactionTestCase` or
`async_to_sync` wrapping, matching how `test_consumers.py` already does it.
`send_group_message` needs the in-memory channel layer, not a live Redis.

**Item 4 (status sweep).**
- Any comparison built from a variable rather than a literal (e.g. an f-string
  in a log line, or `f"skipped:{timer.status}"` at `gameplay/tasks.py:88`) is
  unaffected and must not be "fixed".
- The `status__in=[...]` querysets and the `Q(status="active")` in
  `gameplay/tasks.py:136` must keep identical values — a typo here silently
  changes a sweep's scope rather than erroring.
- `max_length=20` stays; no value grows.
- The migration is choices-only. Confirm `makemigrations` produces exactly one
  `AlterField` and no column alteration before committing.

**Item 5 (reward summaries).**
- `PlayerActivity.get_xp_reward_summary` takes a `duration` override (used by
  offline logging at `progression/services.py:99`); `CharacterActivity`'s does
  not. The helper must not assume one signature.
- `_fmt` returns `int` or `float` depending on integrality — moving it must
  preserve that exactly, since the values land in stored JSON and in frontend
  number formatting.
- Backwards compatibility: old `reward_breakdown` rows keep their existing
  keys. Anything reading them must tolerate a missing key, as
  `useActivityInput.ts:62-65` already does with `!= null` guards.

**Concurrency.** None of the five introduces new concurrency. Item 1 touches a
function called from an async consumer, but the fix is a local control-flow
correction with no new shared state. Item 4 changes no write path. No new
locking, transactions or idempotency controls are needed, and adding any would
be unjustified.

---

## 6. Tests

**New — `gameplay/tests/test_utils.py`** (commit 1, the substantive addition):
- `start_server_timers` in each valid status, and in an invalid one.
- `pause_server_timers` for `completed`/`empty` (no-op) vs other statuses.
- `control_timers` with `"start"`, with `"pause"`, and with an unrecognised
  mode — the last is the regression test for item 1.
- Assert the websocket group message on both the success and failure paths;
  the message shape is the contract the frontend consumes.
- `process_initiation` / `process_completion` success and failure paths. These
  are on the path being re-enabled, so they should be tested even though they
  are currently unreachable from the consumer.

**Existing — modify:**
- `gameplay/tests/test_disconnect_grace.py:275,305,337` patch `control_timers`
  wholesale. Leave the patching, but confirm the mock's call signature still
  matches after item 1.
- After item 4, run the gameplay and api suites; any failure indicates a value
  changed, which is the one thing the sweep must not do.

**Not needed:** items 3 and 5 are documentation and a pure refactor. Item 5's
existing coverage (`test_premium_activity_rewards.py`,
`test_xp_modifiers.py:240-288`, `test_activity_timer_premium.py`) already pins
both summaries' outputs; if those pass unchanged, the extraction is correct.

Per project convention, run individual/scoped test units only — full Vitest and
Playwright suites are the user's to run.

---

## 7. Risks

- **Item 4 sweep changes a stored value.** The highest-consequence mistake
  available here: a status string that differs by a character silently breaks a
  sweep or a queryset with no error. Mitigate by diffing the literal values
  before/after, not just running tests.
- **Item 4 scope creep into `Journey.status`.** It looks like the same change
  and is not. See §4.
- **Item 2 tests written against the buggy behaviour and left that way.** The
  commit-1/commit-2 split exists to prevent this; the assertion must flip.
- **Item 5 treated as licence to unify the multiplier logic.** The reward
  formulas are the most balance-sensitive code in the project. The refactor is
  dict-shaping only.
- **Item 5 renaming a key for tidiness.** Breaks historical `reward_breakdown`
  snapshots. Additive only.
- **Item 1 fixed by making the invalid mode raise.** It is called from an async
  consumer where an exception has a different blast radius than a `False`
  return; match the function's existing failure contract.

---

## 8. Open questions

1. **Modifier stacking (blocks commit 3).** Is unbounded multiplicative
   stacking in `progression/ap.py:73-81` intended, or is a cap wanted before
   more modifier types exist? The comment should record the real answer — I
   won't guess at the game-design reasoning. If a cap is wanted, that's a
   separate plan, not this one.
2. **Player-scope `XpModifier`s (affects item 5's framing).** Player-scope
   modifiers are created and grace-extended
   (`gameplay/services/xp_modifiers.py:169-174`) but never read — the only
   consumer of `get_xp_multiplier()` is `progression/models.py:885`
   (`self.character.…`). Is closing that gap part of the PlayerCharacterLink
   re-enablement? If so, item 5 should document the intended end state rather
   than the current one, and commit 5 should land after that work.
3. **`api/views.py:772-773`** — are `"population_centre": None` and
   `"xp_mods": []` placeholders for the same re-enablement? Not in scope for
   these five, but a one-line comment would prevent the next person retracing
   it.
