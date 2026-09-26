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

Four independent, low-risk commits, ordered safest-first:

1. Replace `"Male"`/`"Female"` string literals with `Character.SexChoices`
   in `lifecycle_services.py` and `relationship_services.py`.
2. Deduplicate `DISCONNECT_TASK_CACHE_KEY` to one source of truth.
3. Introduce a `PROJECT_SRID` constant for `srid=3857`, applied to
   production code (models, services, management commands).
4. Sweep `PROJECT_SRID` into the 30 test files that also hardcode
   `srid=3857`, at your request — split into its own commit since it's
   pure test-fixture churn across 4 apps, separate from the production
   fix in commit 3 (see Design decisions).

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
- 30 test files across `character/tests/` (3), `economy/tests/` (5),
  `locations/tests/` (21, including `factories.py`), and
  `progression/tests/` (1) — replace hardcoded `srid=3857` with
  `PROJECT_SRID` (all exist; full list in Implementation plan, commit 4).

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
- Leave migrations untouched (see Design decisions) — they're historical
  snapshots, not read for the finding's "no named source of truth" problem.

**Commit 4 — sweep `PROJECT_SRID` into test files**
- Replace `srid=3857` with `srid=PROJECT_SRID` (imported from
  `locations.constants`) in the 30 test/fixture files that hardcode it:
  `character/tests/{test_behaviour_services,test_character_location,test_tasks}.py`;
  `economy/tests/{test_capacity_services,test_conversion,test_field_crop,test_planning_services,test_tasks}.py`;
  `locations/tests/{factories,test_assign_workers,test_character_serializers,test_generate_characters,test_generate_fields,test_generate_landarea,test_generate_paths,test_generate_villages,test_import_village_command,test_initial_map_centre_view,test_map_character_detail,test_map_serializers,test_map_viewport,test_map_world_bounds,test_models,test_population_centre_admin,test_population_centre_views,test_population_estimation,test_road_connections,test_schedule,test_wander,test_watabou_import}.py`;
  `progression/tests/test_activity_archive.py`.
- `locations/tests/factories.py` is worth doing first within this commit —
  several of the other test files likely construct points via its
  factories rather than calling `Point(..., srid=3857)` directly, so
  fixing the factory may shrink the remaining per-file literal count
  before touching the rest (check at implementation time; the grep count
  above is call sites, not files that need a factory fix vs. a direct
  literal fix).
- Cross-app commit (4 apps) but mechanical and low-risk — same
  find/replace pattern as commit 3, just a larger file count.

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
- **`PROJECT_SRID` swept into test files too, as a separate commit**: the
  audit's own count ("42 sites") undercounts what a full sweep finds (269
  total, 39 non-migration files, of which 30 are test files each
  hardcoding `srid=3857` in fixture/factory data). Per your request, this
  plan now sweeps both production and test code, but keeps them as two
  commits (3 and 4) rather than one: commit 3 is the finding's actual fix
  (a real "no named source of truth" cost in code someone reads to
  understand the system); commit 4 is mechanical fixture churn across 4
  apps with a much larger, purely additive diff. Splitting them means
  commit 3 alone is still a clean, reviewable unit if you'd rather land
  the production fix first and the test sweep separately, or not at all.
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
- **Commit 4**: none — test-only, same literal value, no behavior change.
  Watch for tests that hardcode `3857` as a bare int (e.g. an SRID
  assertion, `self.assertEqual(obj.location.srid, 3857)`) rather than
  inside a `Point(...)`/field call — those are asserting the *behavior*
  the finding is about, not restating it, so leave the bare literal alone
  in that case rather than replacing it with the constant.

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
- **Commit 4**: no new tests — this commit *is* the test suite. Run the
  affected apps' test modules after the sweep (scoped runs only, per this
  repo's test-running convention) to confirm nothing was mis-edited.

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
- Commit 4: replacing a bare-int SRID assertion (see Edge cases) instead
  of leaving it as a literal — would make a test tautological against its
  own constant instead of verifying the actual stored value. Also: 30
  files is enough that one could plausibly use a *different* SRID
  deliberately (e.g. a WGS84 fixture testing a conversion path) — grep
  each file's context rather than blind find/replace.

## 8. Open questions

- None outstanding — scope now covers both production and test code per
  your request.
