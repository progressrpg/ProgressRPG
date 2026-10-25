# Dead Code and Stale Branches Fixes (Audit §7)

Plan-only. Covers the `minor` findings from
`docs/design-notes/codebase-re-entry-audit.md` §7 ("Dead code and stale
branches") that are safe, mechanical cleanups. Scope confirmed with you
first:

- **`control_timers` `NameError` bug** (`blocks`) — already fixed in
  PR #829 commit 2. Not in this plan.
- **`wander_tick`** (`slows`) — confirmed fully superseded (disabled via
  `locations/migrations/0002_disable_wander_tick_periodic_task.py`,
  replaced by `commute_tick`) and its only consumer (`wander()`, purely
  decorative idle-drift movement) has no other caller. **Left alone per
  your decision** — excluded from this plan, same treatment as PCL.
- **Sun-phase movement chain + `LifeCycleMixin` pregnancy/death system**
  (`slows`) — fully built and tested but unreachable, with no comment
  anywhere recording why. **Confirmed paused-for-later, not dead** —
  excluded from this plan entirely, same treatment as PCL. Not to be
  touched by any future readability-audit work without your say-so.
- **`api/views.py` hardcoded `population_centre`/`xp_mods` placeholders**
  (`minor`) — **PCL path.** Only a one-line explanatory comment, no
  removal, per standing instruction.

This plan covers the five remaining, genuinely-dead, non-PCL `minor`
findings: `day_window()`'s discarded return, `interrupt_current_activity`'s
unused `boost_ended` param, `gameplay/models.py`'s `set_waiting()`/
`compute_elapsed()`, `gameplay/services/timer_service.py`, and two stale
frontend comments.

## 1. High-level strategy

Five small, independent commits, each removing or correcting exactly one
confirmed-dead thing. All verified by direct grep for callers before
inclusion here — nothing in this plan is dead on the audit's word alone.

## 2. Files likely to change

- `character/services/behaviour_services.py` — remove the discarded
  `day_window(behaviour, date)` call at line 92; remove `boost_ended`
  param from `interrupt_current_activity` (exists).
- `character/models/behaviour.py` — remove `boost_ended` param from the
  `interrupt_current_activity` wrapper method (exists).
- `gameplay/models.py` — remove `set_waiting()` and `compute_elapsed()`
  (exists).
- `gameplay/services/timer_service.py` — **delete file** (two unused
  imports, no code, zero importers).
- `api/views.py` — add a one-line comment above the `population_centre`/
  `xp_mods` placeholders (exists). No behavior change.
- `frontend/src/hooks/useActivityTimer.ts` — fix two stale inline
  comments (exists).

## 3. Implementation plan

**Commit 1 — `day_window()` no-op call**
- Delete `day_window(behaviour, date)` at
  `character/services/behaviour_services.py:92` — its return value is
  discarded and nothing else in `generate_day()` depends on it having run
  (it's a pure function with no side effects, confirmed by reading its
  body: three `timezone.make_aware()` calls and a return, no writes).

**Commit 2 — `interrupt_current_activity`'s unused `boost_ended`**
- Remove the parameter from both
  `character/services/behaviour_services.py:interrupt_current_activity`
  and its wrapper at `character/models/behaviour.py:55`. The one caller
  (`gameplay/tasks.py:234`, `end_online_boost`) already calls it with no
  arguments, so no call-site change needed.
- Note: PR #840 (test-coverage-fixes, §6) plans a test that *documents*
  this parameter's no-op status rather than removing it — if that PR
  lands first, its `InterruptCurrentActivityTests` will need updating to
  drop the now-nonexistent parameter from its assertions. Flagged as a
  sequencing dependency, not blocking either PR.

**Commit 3 — `gameplay/models.py` dead methods**
- Remove `set_waiting()` (zero callers anywhere, including tests) and
  `compute_elapsed()` (zero callers; only reference was a commented-out
  log line already not present as live code).
- Leave `get_elapsed_time()` and `apply_elapsed()` untouched — both have
  real callers and are the two half of the §2 `minor` naming finding
  already excluded from that plan.

**Commit 4 — delete `gameplay/services/timer_service.py`**
- Whole-file delete: two import statements, no function/class
  definitions, zero importers anywhere in the codebase (confirmed via
  grep for `timer_service` — only the file's own path, no imports).

**Commit 5 — stale comments**
- `api/views.py` — add a one-line comment above the `"population_centre":
  None` / `"xp_mods": []` block stating these are placeholders for the
  PlayerCharacterLink re-enablement (matching `api/serializers.py`'s
  typed fields and `useBootstrapGameData.ts`'s `info.xp_mods` read), per
  the audit's own suggestion. No value or structure change.
- `frontend/src/hooks/useActivityTimer.ts:19` — the `status` state's
  inline comment lists `"empty", "active", "waiting", "completed"` but
  omits `"paused"`, a real, load-bearing status value (used by `pause()`
  server-side and read by the frontend). Add it.
- `frontend/src/hooks/useActivityTimer.ts:27` — `canResume`'s trailing
  comment ("true after auto-stop fires; cleared on next startActivity or
  stop") actually describes `autoStopCompletion`'s lifecycle, not
  `canResume`'s. Correct it to describe what actually sets/clears
  `canResume` (verify the real trigger at implementation time by reading
  the `setCanResume` call sites in this file).

## 4. Design decisions

- **`boost_ended` removed here, only documented in #840**: #840 (§6, test
  coverage) is about pinning current behavior with tests; this plan (§7,
  dead code) is about removing dead surface area. They target the same
  parameter from two different angles because they're two different
  audit findings on the same line — not a duplicate. The sequencing note
  above exists so whoever implements these two plans doesn't land them in
  an order that breaks the other's tests silently.
- **Comment-only fix for the PCL placeholders, not a `TODO`/`FIXME`
  marker**: matches the tone of other in-repo comments explaining
  deliberate incompleteness (e.g. `Movable`'s cache-set comment,
  `xp_modifiers.py`'s grace-window comment) rather than introducing a new
  marker convention.
- **No new test for the two `useActivityTimer.ts` comment fixes**:
  comments aren't executable; nothing to pin.

## 5. Edge cases

- Commit 2: confirm no other caller of `interrupt_current_activity`
  exists beyond `gameplay/tasks.py:234` before removing the parameter —
  grep confirms this, but re-verify at implementation time in case a
  sibling PR (#835's commit 7/8, PCL-adjacent) has added a new call site
  by the time this is implemented.
- Commit 4: confirm `gameplay/services/` doesn't become an empty
  directory needing `__init__.py` cleanup — check for other files in
  that directory before deleting (it has `xp_modifiers.py` at minimum, so
  the directory stays populated).

## 6. Tests

- Commits 1, 3, 4: no test changes — removing genuinely dead code with no
  test coverage (confirmed: `set_waiting`/`compute_elapsed`/
  `timer_service.py` have no existing tests referencing them, since
  nothing calls them).
- Commit 2: see sequencing note in Implementation plan — coordinate with
  #840 if both are implemented.
- Commit 5: no test changes — comments and non-functional documentation
  only.

## 7. Risks

- Commit 2's cross-PR sequencing with #840 is the main risk in this plan
  — worth calling out explicitly in whichever PR implements second.
- Commit 3: double-check no test *indirectly* exercises `set_waiting()`
  or `compute_elapsed()` through a mock/patch that doesn't show up in a
  plain grep for the function name (e.g. `getattr(timer, "set_waiting")`)
  — unlikely given the codebase's style elsewhere, but worth a second
  pass at implementation time.

## 8. Open questions

- None outstanding — the two genuinely ambiguous items (wander_tick,
  sun-phase/pregnancy-death) were resolved via your answers and excluded
  from this plan's scope entirely.
