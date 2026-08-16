# Plan: Per-building working hours (issue #668)

## Context

`target_role_for` (`locations/services/schedule.py`) currently decides
HOME/WORK for every character from two fixed module constants, `WORK_START`
(08:00) / `WORK_END` (18:00), plus a per-character stagger. This ignores
which building the character actually works at.

`Building` (`locations/models.py`) has a `building_type` choice field but no
concept of opening hours. `CharacterLocation` (`character/models/location.py`)
already links a character to their work `Building` directly via its
`location` FK (`role="work"`, `is_primary=True`) — no intermediate model
needed.

Scope, per the issue: give `Building` type-level default hours with an
optional per-instance override, and have `target_role_for` resolve the work
window from the character's assigned work building, falling back to the
existing constants when the building has no hours. No entry-gating, no
rendering changes, no overnight-wrap handling.

---

## 1. High-level strategy

- Add two nullable `TimeField`s to `Building` (`open_time_override`,
  `close_time_override`) plus a plain-dict module constant
  `BUILDING_TYPE_HOURS` mapping `building_type` → `(open, close)` or `None`.
- Add `open_time`/`close_time` properties on `Building` that resolve
  override → type default → `None`.
- In `target_role_for`, look up the character's primary WORK
  `CharacterLocation`, read its building's `open_time`/`close_time`, and use
  them in place of `WORK_START`/`WORK_END` when both are set; otherwise fall
  back to the constants exactly as today. Stagger logic is unchanged —
  it's applied to whichever start/end was resolved.
- `sync_character_location` needs no changes; it already calls
  `target_role_for` and separately fetches the WORK `CharacterLocation` for
  routing.

---

## 2. Files likely to change

- `locations/models.py` — existing file. Add fields + properties +
  `BUILDING_TYPE_HOURS` constant to `Building`.
- `locations/migrations/000X_building_open_close_hours.py` — new migration,
  generated via `makemigrations`.
- `locations/services/schedule.py` — existing file. Update `target_role_for`
  to resolve hours from the work building.
- `locations/tests/test_schedule.py` — existing file. Add cases for
  override, type-default, and no-hours-fallback, plus stagger-still-applied.
- `locations/admin.py` — existing file, optional. If `Building` is already
  registered with editable fields, consider exposing the two override
  fields; skip if the admin registration is minimal and doesn't need it.

No new services, models, or endpoints — this is additive to two existing
files.

---

## 3. Implementation plan

1. **Model change**: add `open_time_override`/`close_time_override` fields,
   `BUILDING_TYPE_HOURS`, and the `open_time`/`close_time` properties to
   `Building`. Run `makemigrations`.
2. **Schedule logic**: update `target_role_for` to fetch the character's
   primary WORK `CharacterLocation` (`select_related` to avoid an extra
   building query), read `open_time`/`close_time` off its `location`
   (the `Building`), and use them if both are non-`None`; otherwise keep
   `WORK_START`/`WORK_END`. Keep the seconds-since-midnight/stagger
   arithmetic identical, just parameterised on the resolved start/end.
3. **Tests**: extend `test_schedule.py` with the four scenarios called out
   in the issue (override present, type-default only, no hours at all,
   stagger still correct on resolved times).

Each step is a small, independently reviewable commit.

---

## 4. Design decisions

**`BUILDING_TYPE_HOURS` as a plain module constant vs. seeded data**
- Chosen: plain dict constant in `locations/models.py` (or
  `locations/services/schedule.py` — see open question below), matching the
  issue's stated default.
- Alternative: migration/fixture-seeded data, editable without a deploy.
- Reasoning: the building-type list is small and fixed (9 types), matches
  the existing pattern of `BUILDING_TYPES` already being a hardcoded list on
  the model, and avoids adding a new admin-editable data model for a problem
  that doesn't need runtime tuning yet.

**Where hours resolution lives (`Building` property vs. inline in schedule.py)**
- Chosen: `open_time`/`close_time` as properties on `Building`, so any other
  future caller (admin display, a future gating feature) gets the same
  override→default resolution for free.
- Alternative: resolve inline in `target_role_for` only.
- Reasoning: `Building` is the natural owner of its own hours; keeping
  resolution off the model would force every future caller to duplicate the
  override/default/None logic.

**Fallback behavior when hours are partially set**
- Chosen: treat "has hours" as both `open_time` and `close_time` being
  non-`None`; if either resolves to `None`, fall back entirely to the fixed
  constants (matches the issue's explicit test case: "building with no
  hours falls back to constants").
- Alternative: mix a present open with the constant's close.
- Reasoning: partial hours (e.g. only a close time set) isn't a case the
  issue describes and would produce a nonsensical half-defaulted window;
  all-or-nothing is simpler and matches the type-default table where
  entries are `None` (both) or a full pair.

---

## 5. Edge cases

- **No work `CharacterLocation`**: `target_role_for` must keep working for
  characters with no assigned work building (falls back to constants) —
  same as it does today implicitly, since currently there's no building
  lookup at all.
- **Building type not in `BUILDING_TYPE_HOURS`**: treat as `None` (fallback),
  don't raise `KeyError` — use `.get()`.
- **Override set but type default is `None`** (e.g. someone manually gives a
  `residential` building hours): overrides win regardless of type, per the
  issue's "override if set, else type default" ordering.
- **Migration**: purely additive nullable fields, no backfill needed, safe
  on existing rows.
- **Backwards compatibility**: buildings with no override and a `None`-typed
  default behave exactly as before (constants), so existing tests/behaviour
  for buildings without explicit hours don't change.
- **Overnight-wrapping hours**: explicitly out of scope per the issue; not
  handled, and the existing seconds-since-midnight comparison
  (`start <= t < end`) would silently misbehave if a future building type
  ever gets an overnight window — worth flagging in a code comment near the
  new properties or in the follow-up ticket the issue mentions.

---

## 6. Tests

New/modified cases in `locations/tests/test_schedule.py`:
- Work building with `open_time_override`/`close_time_override` set →
  `target_role_for` uses the override window instead of constants.
- Work building with no override but a type with default hours (e.g.
  `mill`) → uses the type default window.
- Work building with a type that has no default hours (e.g. `residential`
  or `communal`, as already used in existing fixtures) and no override →
  falls back to `WORK_START`/`WORK_END` (existing tests already cover this
  path implicitly and should keep passing unchanged).
- Character with no work `CharacterLocation` at all → falls back to
  constants, doesn't error.
- Per-character stagger still applied correctly when hours come from a
  building (reuse the existing stagger test pattern with a building-based
  window instead of the constants).

Possibly a small model-level test for `Building.open_time`/`close_time`
property resolution (override present / type-default only / neither) if not
already fully exercised via the schedule tests above.

---

## 7. Risks

- Forgetting `select_related` when fetching the WORK `CharacterLocation` in
  `target_role_for`, adding a per-character extra query in `commute_tick`'s
  loop (already an N+1-shaped area per the issue's own follow-up note).
- Treating "override or default present but only one of open/close set" as
  a valid window instead of falling back — would produce a confusing
  half-window whether they meant to instead see the full existing
  constants.
- Missing a building type when populating `BUILDING_TYPE_HOURS`, silently
  falling back to constants for that type instead of getting a deliberate
  `None` mapping — should explicitly enumerate all 9 types as the issue
  requests, not just add entries for the ones "obviously" needing hours.
- Breaking the existing stagger arithmetic by refactoring it to take
  start/end as parameters — should keep the internal seconds arithmetic
  identical, just swap in resolved values before the diff, not fold in new
  logic.

---

## 8. Open questions

- Should `BUILDING_TYPE_HOURS` live in `locations/models.py` next to
  `Building`, or in `locations/services/schedule.py` next to
  `WORK_START`/`WORK_END`? Proposal: on the model, since `open_time`/
  `close_time` properties need it there anyway and `schedule.py` shouldn't
  need to know about building-type internals.
- Per the issue itself: should `BUILDING_TYPE_HOURS` eventually become
  editable data (migration/fixture-seeded) rather than a code constant?
  Deferred — plain constant for now, per the issue's stated proposal.
