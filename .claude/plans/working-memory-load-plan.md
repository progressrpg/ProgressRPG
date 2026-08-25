# Working-memory load — decomposing the audit's blocks/slows findings

Addresses every `blocks` and `slows` row in
`docs/design-notes/codebase-re-entry-audit.md` §1 (Working-memory load). The
`minor` row (`progression/models.py` file size) is out of scope — no severity
threshold was crossed for it, and splitting a 1185-line models file is a
bigger structural call than this plan's other items.

Background: `docs/design-notes/codebase-re-entry-audit.md` §1.

---

## 1. High-level strategy

Seven independent findings, seven independent commits. None of them share a
call path with each other, so there is no ordering dependency between them —
ordering below is by risk, cheapest/safest first, so a bad commit is easy to
isolate and revert without blocking the rest.

The common technique is **extract, don't redesign**: pull an existing block of
a long function out into a private helper (or, for the delegate-hop pattern,
collapse a hop) with the same inputs/outputs and no behaviour change. Nothing
here changes what any function does — only how many places you have to read to
see it doing it.

**Standing caution carried over from the audit itself**: the character-link
(PCL) path is mid-reactivation, not dead. Two items below
(`TimerConsumer.connect()`, `gameplay/utils.py`'s `process_initiation` /
`process_completion`) sit directly on that path. Their plan is scoped to
line-for-line extraction with no behavioural change, and flagged so
implementation can be checked against whatever PCL work is in flight before
landing.

---

## 2. Files likely to change

All existing files; no new files except tests.

| File | Why |
|---|---|
| `gameplay/consumers.py` | Split `TimerConsumer.connect()` (99 lines) into named steps. |
| `character/services/behaviour_services.py` | Split `generate_day()` (126 lines) into named steps; extract the day-shape constants (also feeds §4 below, but that's a separate plan/finding). |
| `character/models/character.py`, `character/models/behaviour.py`, `character/services/lifecycle_services.py`, `character/services/behaviour_services.py` | Collapse the `Mixin method → lifecycle_*`/`behaviour_services` one-line delegate hop. |
| `locations/models.py`, `locations/services/movement.py` | Remove the module-level `find_path`/`Movable.go_home`/`Movable.go_outside` wrapper layer. |
| `gameplay/models.py` | Split `ActivityTimer.complete()` (111 lines) into named steps. |
| `api/views.py` | Split `FetchInfoAPIView.get()` into named steps. |
| `frontend/src/components/Map/Map.tsx` | Extract effect groups into custom hooks; no JSX/behaviour change. |
| Existing test files for each touched module | Re-run/extend to confirm behaviour is unchanged; add direct coverage where an extracted step had none. |

---

## 3. Implementation plan

### Commit 1 — collapse the `LifeCycleMixin` / `Behaviour` delegate hop

- `character/models/character.py`'s `LifeCycleMixin` methods (`get_age`,
  `die`, `is_alive`, `get_romantic_partners`, `is_fertile`,
  `can_reproduce_with`, `attempt_pregnancy`, `start_pregnancy`,
  `handle_childbirth`, `handle_miscarriage`, `get_miscarriage_change`) and
  `character/models/behaviour.py`'s `Behaviour` methods (`generate_day`,
  `sync_to_now`, `advance`, `delete_day`, `get_current_activity`,
  `interrupt_current_activity`, `_day_window`) are each a one-line call into
  `lifecycle_services.lifecycle_<name>(self, ...)` /
  `behaviour_services.<name>(self, ...)`.
- Rename the service functions to drop the `lifecycle_` prefix
  (`lifecycle_get_age` → `get_age`, etc.) — `behaviour_services` functions
  already have no prefix, so only `lifecycle_services.py` needs the rename.
- Keep the mixin/model methods as the public API (`character.get_age()`),
  since callers throughout the codebase already use them and that's the
  correct place for the public surface — but each now reads as
  `return lifecycle_services.get_age(self)`, so a search for `def get_age`
  in `lifecycle_services.py` matches directly instead of needing the prefix.
- No behaviour change; this is a rename plus mechanical find/replace of call
  sites inside `lifecycle_services.py` (functions there call each other by
  name) and any direct `lifecycle_services.lifecycle_*` callers outside the
  mixin (grep to confirm — expected to be none, since the mixin is the only
  documented entry point).

### Commit 2 — remove the `Movable` wrapper layer for `find_path`/`go_home`/`go_outside`

- `locations/models.py:22-23` (module-level `find_path`) and the
  `Movable.go_home` / `Movable.go_outside` methods are pure one-line
  delegates to `locations/services/movement.py`.
- Grep all call sites of `find_path(`, `.go_home()`, `.go_outside()` across
  the codebase (`locations/`, `character/`, `gameplay/`, tests).
- For `go_home`/`go_outside`: keep them as `Movable` methods (they're used as
  methods on `Character` instances at call sites, e.g.
  `character.go_home()`), but confirm each just forwards — if so, leave the
  method but point its docstring at the real implementation rather than
  removing it outright, since `movable.go_home()` reading naturally from a
  `Character` instance is worth keeping as an entry point. The finding is
  about the module-level `find_path` wrapper being a third layer for no
  reason — that one is removed, callers switch to importing
  `locations.services.movement.find_path` directly.
- `get_nearby_outside_nodes` / `pick_random_outside_node` /
  `set_destination` on `Movable` are the same one-line-delegate shape but
  weren't flagged in the audit; leave them alone — don't expand scope beyond
  the finding.

### Commit 3 — extract day-shape constants in `behaviour_services.generate_day`

- Pull the inline time literals (`time(7, 0)`, `15`, `time(17, 30)`, `10`,
  `time(22, 30)`, `time(23, 0)`, and the `2` in `rng.sample(..., 2)`) into
  module-level named constants at the top of `behaviour_services.py`
  (`WAKE_TIME`, `WAKE_JITTER_MINUTES`, `DINNER_TIME`, `DINNER_JITTER_MINUTES`,
  `LEISURE_END_TIME`, `WIND_DOWN_END_TIME`, `WORK_ACTIVITIES_PER_DAY`).
- This is also audit finding §4 (`character/services/behaviour_services.py:90`,
  magic numbers), grouped here because it's touched by the same function
  split in commit 4 below and doing it first makes that split read cleaner.
  It does **not** address the two `blocks`-severity §4 findings on the same
  function (no rationale for the day shape / no rationale for "exactly two
  work activities") — those need a design answer from you, not a rename, and
  are out of scope for this plan.

### Commit 4 — split `behaviour_services.generate_day()` into named steps

- Extract three private helpers called in sequence from `generate_day`:
  - `_compute_day_blocks(behaviour, date, rng)` → returns the `cleaned` list
    of `(activity_definition, start, end)` tuples (today's block-timing math
    plus the jitter and the overlap-cleanup loop at lines ~115-125).
  - `_replace_future_activities(behaviour, date, sleep_end, is_past)` → the
    `replace_future` delete branch (lines ~134-150).
  - `_create_activities(behaviour, cleaned, is_past)` → the creation loop
    (lines ~152-170).
- `generate_day` itself becomes: resolve `rng`/`is_past`, call the three
  helpers in order, return `created`. Still one function, but each concern
  is named and independently readable; `character/utils.py`,
  `locations/services/schedule.py`, `progression/models.ActivityDefinition`
  are no longer all needed open at once to trace a single change — only the
  helper relevant to that change is.
- No behaviour change: this is a pure extraction, same statements in the
  same order, `@transaction.atomic` stays on the outer `generate_day`.

### Commit 5 — split `ActivityTimer.complete()` into named steps

- `gameplay/models.py:401-511`. Extract:
  - `_apply_client_elapsed(self, client_elapsed_seconds, completion_source)`
    — the auto-completion elapsed-time reconciliation (lines ~452-465).
  - `_backfill_started_at(self, pre_complete_start_time)` — the
    `started_at is None` backfill branch (lines ~471-485), including its
    local `logical_date_for` import.
  - `_award_and_check_goals(self)` — reward summary, `activity.complete`,
    `player.add_activity`, `check_and_award_daily_goals`, and assembling the
    final `reward_summary` dict (lines ~487-503), including its local
    `check_and_award_daily_goals` import.
- `complete()` keeps the `transaction.atomic()` block, the row lock, the
  early-return guards (no activity / already completed by another process),
  and calls the three helpers plus `self.reset()` in order.
- No behaviour change: same statements, same lock scope, same order.

### Commit 6 — split `FetchInfoAPIView.get()` into named steps

- `api/views.py:864-915`. Extract:
  - `_sync_player_state(self, player)` — `track_user_session`,
    `_ensure_activity_timer_consistency`, the `last_seen` save,
    `handle_online_login` (lines ~871-879).
  - `_build_response_data(self, request, player, build_number)` — assembling
    the `data` dict (lines ~886-907), unchanged field-for-field.
- `get()` becomes: resolve `player`/`build_number`, call
  `_sync_player_state`, resolve `login_state_data`/`game_settings`, call
  `_build_response_data` inside the existing `try`/`except`, return.
- **Flag for coordination**: this endpoint currently hardcodes
  `"character": None`, `"population_centre": None`, `"xp_mods": []` — visibly
  mid-transition for the PCL reactivation. Check with whoever is doing that
  work before landing this commit, in case it conflicts with an in-flight
  change to the same method. The split itself doesn't touch those three
  lines' values, only where they're assembled.

### Commit 7 — split `TimerConsumer.connect()` into named steps

- `gameplay/consumers.py:137-235` (current file; line numbers have likely
  drifted since the audit — re-locate by method name at implementation
  time). Extract, in the order they currently run:
  - `_reject_duplicate_connection(self)` → the already-connected check plus
    `await self.close()` (returns a bool: whether the caller should stop).
  - `_load_player_state(self, user)` → `set_player_and_character`, setting
    `self.player`/`self.character`/`self.link`/`self.player_group`, and the
    pending-disconnect-task revocation.
  - `_start_session(self)` → `register_connection`, starting the heartbeat
    task, the two `group_add` calls, `self.accept()`, `broadcast_online_count`,
    `_send_pending_messages`, fetching `self.activity_timer`.
  - Leave the final "successful connection" / "no active character"
    `send_json` calls inline in `connect()` — they're the observable
    outcome, not setup, and are what a reader wants to see last.
- `connect()` becomes: resolve `user`/`is_authenticated`, early-return if not
  authenticated, call the three helpers in order, send the two client
  messages.
- **This is the PCL-adjacent one.** `self.link` and `self.activity_timer` are
  exactly the state the audit calls out as "read 150 lines away in
  `disconnect()`" — this commit does not change disconnect() or move where
  that state lives, only how connect() is broken into named steps that set
  it. Coordinate with any in-flight PCL work touching `connect()` before
  landing; if there's an active branch touching this method, this commit
  should be rebased onto it rather than the reverse.

### Commit 8 — extract `process_initiation`/`process_completion` naming clarity (§2 companion, done here for locality)

Not in scope — this is audit finding §2 (naming clarity), not §1. Skipped;
listed in Open Questions below in case you want it folded in.

### Commit 9 — decompose `Map.tsx`'s effect groups into custom hooks

- `frontend/src/components/Map/Map.tsx` (890 lines), ~15 `useEffect`s / ~10
  `useMemo`s in one component body.
- Group the effects by the state they own (this needs a read of the actual
  effect bodies at implementation time to group correctly; the grouping
  below is a starting hypothesis from the audit's description):
  - Map lifecycle (create/destroy the MapLibre instance, `mapReady`,
    `mapWrapperEl`) → `useMapInstance`.
  - Village/building GeoJSON source sync (`refreshVillageSource` and the
    effects that call it) → `useVillageSource`.
  - Walker animation (`walkersRef`, the effect that writes it, the effects
    that read it) → `useWalkerAnimation`. This is the one the audit calls
    out by name as split across "one effect and two others 100+ lines
    apart" — collecting it into one hook with an explicit return contract
    (e.g. `{ walkersRef, tick }`) removes the need to jump around the file
    to see the full read/write cycle.
  - Tooltip/hover state → `useMapHoverState` (already fairly localized;
    lower priority within this commit).
- Hooks take `mapRef`/`sourceRef`/whatever refs they need as arguments and
  return the state Map.tsx's JSX needs — same pattern as the file's existing
  `openDetail`/`handleFlyToDetail` `useCallback`s, just promoted to
  module-level hooks instead of inline closures.
- No behavioural change; this is a JS-level extraction (move `useEffect`
  bodies into hook files) with identical dependency arrays. Playwright's
  existing Map e2e coverage (if any — check `frontend/e2e` for map specs) is
  the regression backstop; this is exactly the kind of change that's easy to
  verify by eyeballing the diff (each hook is a cut/paste of contiguous
  lines) but easy to break subtly (a missed dependency, a ref passed by
  value instead of by reference), so review the diff for exact line-for-line
  moves rather than rewrites.

---

## 4. Design decisions

- **Extract-in-place over restructuring the module.** Alternative considered:
  moving each split-out helper into its own service module (e.g.
  `gameplay/services/activity_timer_completion.py`). Rejected — the audit's
  complaint is line count and mixed concerns within one function, not that
  the function is in the wrong file. Private module-level (or class-private)
  helpers fix the stated problem with a smaller diff and no new import
  surface to learn.
- **Rename over removing the delegate pattern entirely** (commit 1).
  Alternative: fold `lifecycle_services`/`behaviour_services` functions
  directly onto the model as real methods, removing the service module
  split altogether. Rejected — that's a bigger architectural change than the
  finding asks for (the finding is about the `lifecycle_` prefix defeating
  grep, not about the service-module pattern itself, which is used
  consistently elsewhere in the codebase per audit §5), and it would touch
  far more call sites for no readability gain beyond what the rename already
  gets.
- **Keep `Movable.go_home`/`go_outside` as methods, remove only
  `find_path`'s module-level wrapper** (commit 2). Alternative: remove all
  three wrapper layers uniformly. Rejected — `character.go_home()` reads
  correctly as "the character goes home" at call sites; `find_path(a, b)`
  as a bare module-level function has no such affordance, since it doesn't
  read naturally as an operation *on* anything. Treating them differently is
  matching the fix to why each one is confusing, not applying one rule
  everywhere.
- **Split Map.tsx by state ownership, not by effect count.** Alternative:
  split into N hooks of roughly equal size. Rejected — the audit's actual
  complaint is that `walkersRef` is written in one place and read 100+ lines
  away, i.e. an ownership problem, not a length problem. Grouping by what
  state each effect touches directly fixes that; grouping by size wouldn't.

---

## 5. Edge cases

- **No migrations involved** — every change here is a pure code
  reorganization (Python function/method splits, a service-function rename,
  a frontend hook extraction). No model, field, or schema changes.
- **Import cycles**: `lifecycle_services.py` renamed functions must still
  resolve within that module's existing import graph — check for any
  circular-import guards currently relying on the `lifecycle_` prefix name
  specifically (unlikely, but confirm by running the app boot / existing
  test imports).
- **`transaction.atomic()` / `select_for_update()` scope must not move**:
  commits 4 and 5 both wrap logic that's currently inside a lock. The
  extracted helpers must stay called *from inside* the same atomic block —
  don't accidentally widen or narrow the locked window by extracting a
  helper that itself opens a new transaction or that gets called before the
  lock is acquired.
- **`generate_day`'s `rng` must stay single-instance per call**: the three
  helpers in commit 4 that need randomness (`_compute_day_blocks`) must
  receive the same `random.Random(seed)` instance `generate_day` constructs,
  not each construct their own — otherwise the deterministic-seed property
  (same character+date always generates the same day) breaks.
- **Frontend dependency arrays**: commit 9's biggest real risk. An extracted
  hook that drops a ref from its `useEffect` dependency array (or adds one
  that wasn't there) changes when the effect re-runs. Diff each hook against
  the original effect body line-for-line rather than reformatting.
- **Backwards compatibility**: none of these functions/methods are called
  from outside their current module boundary in a way that changes — public
  method names (`character.get_age()`, `timer.complete()`, `character.go_home()`)
  are unchanged; only private internals move.

---

## 6. Tests

- **Commits 1–8 (backend)**: no new test files needed if existing coverage
  already exercises these paths — confirm before writing anything new:
  - `character/tests/test_behaviour_services.py` covers `generate_day` /
    `delete_day` already (per audit §6) — re-run after commits 3–4 to
    confirm identical output for a fixed seed.
  - `gameplay/tests/` — check for existing `ActivityTimer.complete()`
    coverage; if thin, this is a good moment to add a test asserting the
    full reward-summary shape survives the split (commit 5).
  - `api/tests/` — check for `FetchInfoAPIView` coverage; add one if the
    hardcoded `character`/`population_centre`/`xp_mods` fields aren't
    currently asserted, so the split (commit 6) has something pinning the
    response shape.
  - `gameplay/tests/test_disconnect_grace.py` already exercises `connect()`
    indirectly — check it still passes unmodified after commit 7; the audit
    notes `connect()`/`disconnect()` interaction is undertested overall, but
    adding that coverage is bigger than this plan (see Open Questions).
  - Lifecycle/`Movable` methods (commits 1–2): grep for existing tests
    calling `get_age()`, `go_home()`, `find_path()` directly and confirm
    they still pass; these are rename/removal changes so any test currently
    importing `lifecycle_services.lifecycle_get_age` by name needs updating
    to the new name.
- **Commit 9 (frontend)**: check `frontend/e2e` for existing Map specs, run
  them scoped (per this repo's rule against running the full Playwright
  suite) against the refactored component. If no walker-animation e2e
  coverage exists, that's a gap this plan surfaces but doesn't fill —
  flagged in Open Questions.

---

## 7. Risks

- **Silent behaviour drift in the extracted helpers** — the most likely
  mistake is a helper that looks like a faithful cut/paste but subtly
  reorders a side effect (e.g. saving before vs. after a related field is
  set). Mitigate by diffing statement order against the original, not just
  re-reading the new code for correctness.
- **Widening or narrowing a lock's scope** (commits 4, 5) — pulling a
  DB-writing step out of the `atomic()`/`select_for_update()` block by
  mistake would reintroduce exactly the race conditions the surrounding
  comments describe as deliberately prevented.
- **Losing the deterministic-seed property in `generate_day`** — passing
  `rng` incorrectly (e.g. a helper reseeding its own `random.Random`)
  silently breaks reproducibility without raising anything; there's no test
  today that would obviously fail loudly (check whether
  `test_behaviour_services.py` actually asserts determinism, or just
  "doesn't raise" — if the latter, this risk is currently unguarded).
- **Landing commit 6 or 7 out of step with in-flight PCL work** — both touch
  files where character-link reactivation is actively landing. A conflict
  here is a merge/coordination problem, not a design problem; the mitigation
  is checking in before landing rather than anything in the code itself.
- **Frontend hook extraction changing effect timing** — React re-runs effects
  based on dependency array identity; moving a `useMemo`'s result into a
  different hook file can change whether two effects that used to be
  adjacent (and thus batch predictably) now run in a different relative
  order. Low risk given MapLibre's imperative API doesn't depend on render
  order the way DOM-diffing would, but worth an explicit visual smoke-test
  (start dev server, load the map, watch a character walk) before calling
  commit 9 done, consistent with this repo's UI-change testing convention.

---

## 8. Open questions

- Should commit 8 (`process_initiation`/`process_completion` naming — audit
  §2, not §1) be folded into this branch, or left for a separate pass since
  it's a different audit category? Listed here but not planned in detail;
  left out of the commit sequence above pending your answer.
- Two `blocks`-severity findings live on the same function this plan splits
  (`generate_day`'s day-shape rationale and "why exactly two work
  activities", both audit §4) but need a game-design answer, not a
  refactor. Do you want those raised as a follow-up now, or later?
- Is there Playwright coverage for the Map's walker animation today? If not,
  commit 9 ships without a regression backstop beyond manual smoke-testing —
  worth deciding whether that's acceptable or whether a minimal walker e2e
  test should be added first.
- Confirmed groupings for commit 9's hooks are a hypothesis from reading
  effect declarations, not full effect bodies (890 lines wasn't fully read
  for this plan). Implementation should re-derive the grouping from the
  actual effect contents before extracting, and the three-hook split named
  here may turn out to be four or two once the real dependencies are
  visible.
