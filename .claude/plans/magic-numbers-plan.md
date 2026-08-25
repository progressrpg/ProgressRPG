# Magic Numbers and Strings Fixes (Audit §4)

Plan-only. Covers the remaining `blocks`/`slows`/`minor` findings from
`docs/design-notes/codebase-re-entry-audit.md` §4 ("Magic numbers and
strings") that aren't already handled elsewhere:

- **`Timer.STATUS_CHOICES`** (`blocks`) — already resolved via PR #829.
- **`locations/models.py:296` `Journey.status` / `place_characters.py`'s
  `"cancelled"`** (`blocks`) — already planned via PR #836
  (`journey-status-choices-plan.md`).
- **`behaviour_services.py` day-shape constants** (`slows`) — already
  folded into PR #835 as commit 3 (`working-memory-load-plan.md`).

This plan covers what's left: the `sex == "Male"/"Female"` literals
(`slows`) and both `minor` findings (`DISCONNECT_TASK_CACHE_KEY`
duplication, hardcoded `srid=3857`).

## 1. High-level strategy

Three independent, low-risk commits, ordered safest-first:

1. Replace `"Male"`/`"Female"` string literals with `Character.SexChoices`
   in `lifecycle_services.py` and `relationship_services.py`.
2. Deduplicate `DISCONNECT_TASK_CACHE_KEY` to one source of truth.
3. Introduce a `PROJECT_SRID` constant for `srid=3857`, applied to
   **production code only** — not the 30+ test files that also hardcode
   it (see Design decisions for why this is deliberately scoped down from
   the audit's "42 sites").

## 2. Files likely to change

- `character/services/lifecycle_services.py` — replace 3 literal `"Male"`/
  `"Female"` comparisons and 1 literal assignment with `SexChoices` (exists).
- `character/services/relationship_services.py` — replace 3 dict literals
  keyed by `"Male"`/`"Female"` (exists).
- `character/models/character.py` — no change; `SexChoices` already exists
  at line 341, this plan only adds consumers of it.
- `gameplay/consumers.py`, `gameplay/tasks.py` — remove the duplicate
  `DISCONNECT_TASK_CACHE_KEY` definition from one, import from the other
  (both exist).
- `locations/constants.py` — **new file**, following the existing
  `economy/constants.py` pattern already used in this codebase.
- `locations/models.py`, `locations/services/movement.py`,
  `locations/services/watabou_import.py`,
  `locations/management/commands/{show_map,import_village,generate_landarea,generate_characters,populate_interiors}.py`
  — replace hardcoded `srid=3857` with `PROJECT_SRID` (all exist).

## 3. Implementation plan

**Commit 1 — `SexChoices` instead of string literals**
- `lifecycle_services.py:56-59` (`lifecycle_can_reproduce_with`): replace
  `instance.sex == "Male"` / `"Female"` with
  `Character.SexChoices.MALE` / `.FEMALE`.
- `lifecycle_services.py:91` (`lifecycle_handle_childbirth`): replace
  `sex="Male" if randint(0, 1) == 0 else "Female"` with the `SexChoices`
  members. Note `SexChoices` has a third member, `OTHER`, not touched by
  this call (childbirth only ever assigns two sexes) — no behavior change,
  just literal → enum member.
- `relationship_services.py:154-156`: replace `_MARRIAGE_LABELS`,
  `_PARENT_LABELS`, `_CHILD_LABELS` dict keys `"Male"`/`"Female"` with
  `SexChoices.MALE`/`SexChoices.FEMALE` (a `TextChoices` member compares
  and hashes equal to its string value, so dict lookups by
  `other_sex` — itself a plain string from the DB — keep working
  unchanged).
- Both files need `from character.models import Character` (or
  `SexChoices` directly) — check for existing import cycles;
  `lifecycle_services.py` already imports `Character` lazily inside
  functions (per the existing pattern in that module) to avoid a circular
  import with `character/models`, so follow the same lazy-import style
  rather than a top-level import.

**Commit 2 — dedupe `DISCONNECT_TASK_CACHE_KEY`**
- Keep the definition in `gameplay/tasks.py:21` (it's read there in more
  places: `get_scheduled_disconnect_task`-style lookups at lines 75, 87,
  94, 108, 117) and import it into `gameplay/consumers.py`, removing the
  duplicate at `consumers.py:28`.
- Check for an import cycle: `tasks.py` doesn't appear to import from
  `consumers.py` today, so `consumers.py` importing from `tasks.py` should
  be safe — confirm at implementation time.

**Commit 3 — `PROJECT_SRID` constant**
- Add `locations/constants.py` with `PROJECT_SRID = 3857` and a short
  comment on what it is (Web Mercator, the project's working CRS for all
  in-game coordinates).
- Replace `srid=3857` with `srid=PROJECT_SRID` at all production
  (non-test, non-migration) call sites: `locations/models.py` (11 field/
  `Point(...)` definitions), `locations/services/movement.py` (2),
  `locations/services/watabou_import.py` (2 default kwargs), and the 5
  management commands listed above.
- Leave migrations and test files untouched (see Design decisions).

## 4. Design decisions

- **`SexChoices` via lazy import, not top-level**: matches
  `lifecycle_services.py`'s existing pattern (it already does
  `from character.models import Character` inside
  `lifecycle_handle_childbirth`, not at module level) — almost certainly
  to avoid a `character.models` ↔ `character.services` import cycle.
  Alternative considered: top-level import — rejected without verifying
  the cycle doesn't exist; safer to match the established local
  convention.
- **`DISCONNECT_TASK_CACHE_KEY` lives in `tasks.py`, not a shared
  `constants.py`**: `gameplay/tasks.py` already has more read/write sites
  for this key than `consumers.py`, and a `gameplay/constants.py` would be
  a new file for a single constant. Alternative considered: new
  `gameplay/constants.py` — rejected as unnecessary abstraction for one
  value; can revisit if a second cross-module gameplay constant appears.
- **`PROJECT_SRID` scoped to production code, not the ~230 test-file
  occurrences**: the audit's own count ("42 sites") undercounts what a
  full sweep finds (269 total, 39 non-migration files, of which ~30 are
  test files each hardcoding `srid=3857` in fixture/factory data). This is
  a `minor` finding; rewriting 30 test files' fixture literals for a
  cosmetic constant is disproportionate churn for a minor issue and adds
  merge-conflict risk against any in-flight test changes. Production code
  (models, services, management commands) is where "no single named
  source of truth" actually costs a reader something — that's what this
  commit fixes. Alternative considered: sweep everything including tests
  — rejected as scope creep beyond what the finding's severity warrants;
  flagged as an open question below in case you'd rather do the full
  sweep.
- **New `locations/constants.py` file**: mirrors the existing
  `economy/constants.py` pattern already in the codebase, so this is
  reuse of an established convention, not a new abstraction.

## 5. Edge cases

- **Commit 1**: `TextChoices` members are string subclasses, so
  `dict[SexChoices.MALE]` and `dict["Male"]` are equivalent — confirmed no
  behavior change to `household_relationship_label`'s lookups, which
  receive `other_sex` as a plain DB string.
- **Commit 2**: none — same string value, same format method, just one
  definition instead of two.
- **Commit 3**: field-level `srid=PROJECT_SRID` kwargs resolve to the same
  value (3857) Django already has recorded, so `makemigrations` should
  produce no new migration — confirm at implementation time (no Django
  env in this session to verify directly).

## 6. Tests

- **Commit 1**: existing `character/tests/` coverage for
  `lifecycle_can_reproduce_with` and `household_relationship_label`
  continues to pass unmodified (same string values, just sourced from the
  enum). No new tests needed — pure literal-to-enum substitution.
- **Commit 2**: no new tests — existing `gameplay/tests/` coverage
  exercising disconnect-task scheduling/cancellation already tests the
  cache key indirectly.
- **Commit 3**: no new tests — no behavior change. Spot-check one
  management command manually (can't run Django management commands in
  this session) at implementation time.

## 7. Risks

- Commit 1: missing that `lifecycle_services.py` needs the lazy-import
  pattern and introducing a real circular import — verify at
  implementation time by running the affected test module.
- Commit 2: picking the wrong module to keep the definition in causes an
  import-order issue if there's a hidden cycle — check both directions
  before implementing.
- Commit 3: touching a migration file by mistake while sweeping — the
  plan explicitly excludes `*/migrations/*.py`, worth double-checking the
  diff doesn't touch any.

## 8. Open questions

- Should commit 3 also sweep the ~30 test files hardcoding `srid=3857`,
  or is production-code-only the right scope for a `minor` finding? Plan
  above assumes production-only; happy to widen it if you'd rather do the
  full sweep in the same PR.
