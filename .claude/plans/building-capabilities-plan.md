# Plan: Multi-role economic buildings via building capabilities

## Context

Today, "what a building can produce" is entirely encoded in
`Building.building_type` (a single string): `economy/tasks.py`,
`economy/services/capacity_services.py`, `locations/services/watabou_import.py`
and `locations/management/commands/spawn_villages.py` all `filter(building_type="mill")`
etc. A building can only ever do one economic job, and small villages
(see the Ashenford investigation) can end up missing a whole role
(no bakery) purely because of import ordering, with no way to say
"the communal building also bakes."

Goal: let a building hold **multiple capabilities** (e.g. a `communal`
building can mill *and* bake), and let village-level economic planning
allocate demand across whatever capabilities actually exist, rather than
assuming one fixed building type per role forever. Worker assignment
(`CharacterLocation(role=WORK)`, `workers_present(building)`) is **not**
redesigned here - buildings still host workers per-building, not
per-capability, until a later plan needs that granularity.

---

## 1. Conceptual model & terminology

Five layers, kept distinct so "capability" (what a building *can* do)
never gets confused with `CharacterLocation.Role` (home/work) or
`RelationshipRole` (spouse/mentor), which already own the word "Role" in
this codebase:

| Layer | Concept | Lives on |
|---|---|---|
| Physical infrastructure | `Building` / `building_type` | `locations.Building` (unchanged) |
| **Building capability** | e.g. `milling`, `baking`, `farming` | **new**: `BuildingCapability` (one row per building+activity) |
| Economic activity | the fixed vocabulary of production roles | **new**: `EconomicActivity` choices (module-level, not a model) |
| Village economic planning | demand → required capacity → allocation across capable buildings | `economy.services.capacity_services` (evolves) |
| Worker presence | who's physically at a building | `workers_present(building)` (unchanged for now) |

Naming: use **"capability"** for what a building can do, and **"economic
activity"** (`EconomicActivity`) for the fixed enum of production roles
(`milling`, `baking`, `farming`). Avoid "role" entirely for this concept -
`CharacterLocation.Role` and `RelationshipRole` already mean something
specific and unrelated (home/work location, family/relationship role).
Avoid "job"/"occupation" too - `unify-work-flavor-with-jobs-plan.md`
already uses "job" loosely for the *flavor-text* work activity system
(`WORK_ACTIVITIES_BY_BUILDING_TYPE`), which is a different, presentational
concept from economic production capacity.

`granary` (storage) and `field_shelter` (farming presence) are left out of
the capability model for now - see Design decisions.

---

## 2. Files likely to change

- `economy/models.py` - **existing**. Add `BuildingCapability` model
  (FK to `locations.Building`, `activity` choice field).
- `economy/constants.py` - **existing**. Add `EconomicActivity` choices
  (or a plain `TextChoices` class) alongside the existing goods/rate
  constants - this is the shared vocabulary both the model and services
  import.
- `economy/migrations/` - **new migration** for `BuildingCapability`, plus
  a **new data migration** to backfill capabilities from every existing
  building's current `building_type` (mill → milling, bakery → baking,
  field_shelter → farming), so no existing village silently loses
  capacity the day this ships.
- `economy/services/capacity_services.py` - **existing**. `find_mill`/
  `find_bakery` (and the `mills =`/`bakeries =` lookups inside
  `population_capacity_report`) move from `building_type=` filters to
  `buildings.filter(capabilities__activity=...)`. `workers_present` is
  untouched.
- `economy/tasks.py` - **existing**. The three `Building.objects.filter(
  building_type="mill"/"bakery")` loops in `advance_mill_economy_tick`/
  `advance_bakery_economy_tick` switch to filtering by capability instead,
  so a communal building with both capabilities gets ticked for both.
- `economy/services/planning_services.py` - **existing**, mostly
  unaffected. `RoleRequirement.building_type` becomes the activity name
  it already conceptually is (see Design decisions - possibly just a
  rename, no behaviour change) since it's already
  building-type-agnostic in spirit (recommends a *count*, not a specific
  building).
- `locations/services/watabou_import.py` / `spawn_villages.py` -
  **existing**, changed last. Once capabilities exist, importers can
  assign capabilities to a `communal`/generic building type when they run
  out of dedicated special-building slots, instead of silently dropping
  the role. (Left as a follow-up - see Recommended first step.)
- `economy/management/commands/economy_status.py` - **existing**.
  `_print_building` gains a capabilities line; capacity lines already
  read from `population_capacity_report`, so no logic change needed
  there once capacity_services is updated.
- `economy/admin.py` (if it exists / registers `Building`-adjacent
  models) - check and register `BuildingCapability` for visibility.
- New tests: `economy/tests/test_capacity_services.py` (extend),
  `economy/tests/test_models.py` or a new `economy/tests/test_capabilities.py`.

---

## 3. Implementation plan

Small, sequential PRs, each independently shippable and behaviour-preserving
until the final step:

1. **Add `EconomicActivity` vocabulary + `BuildingCapability` model.**
   Model only, migration only, no callers changed yet. Include the
   backfill data migration in the same PR so the schema and its
   initial data land atomically for every environment (dev, staging,
   prod all replay migrations identically).
2. **Point `capacity_services.find_mill`/`find_bakery`/`find_granary`-
   equivalent-for-milling/baking and the `mills =`/`bakeries =` queries
   in `population_capacity_report` at `BuildingCapability` instead of
   `building_type`.** `find_granary`/farming still use `building_type`
   (see Design decisions - granary/field_shelter deliberately out of
   scope). Existing tests should pass unchanged since the backfill
   migration guarantees identical query results on existing data.
3. **Point `economy/tasks.py`'s three `building_type="mill"/"bakery"`
   queryset filters at capability instead.** This is the change that
   actually lets a multi-capability building get ticked for both roles.
4. **Surface capabilities in `economy_status`** (diagnostic command) so
   capability assignment is inspectable without a DB shell.
5. **(Follow-up, separate plan) Update `spawn_villages.py`/
   `watabou_import.py`** to assign capabilities to a generic/communal
   building when dedicated building types run out, closing the
   Ashenford-style gap this investigation started from.

Steps 1-4 constitute this plan; step 5 is called out but intentionally
deferred (see Recommended first step).

---

## 4. Design decisions

**a. New `BuildingCapability` model vs. a JSON/array field on `Building`.**
Chosen: a separate model (one row per building+activity), not a
`JSONField` or `ArrayField` on `Building`. Alternative considered: an
`activities = ArrayField(CharField)` column directly on `Building`.
Rejected because `GoodsStock`/`GoodsConversionState`/`FieldCrop` already
establish the pattern of small satellite models keyed by `building`
(`economy/models.py`) rather than composite fields on `locations.Building`
- economy concerns stay in the `economy` app, not `locations`. A real
row also gets a normal FK/queryset filter (`buildings__filter(
capabilities__activity="baking")`), works with `select_related`/
`prefetch_related` the same way the rest of this codebase already
queries, and leaves room for a later per-capability field (e.g. a
capability-level enabled/disabled flag) without a schema rewrite of
`Building` itself.

**b. Keep `building_type` on `Building`, don't remove or replace it yet.**
Chosen: `BuildingCapability` is additive; `building_type` keeps driving
`BUILDING_TYPE_HOURS`/`open_time`/`close_time` and display/flavor-text
concerns (`WORK_ACTIVITIES_BY_BUILDING_TYPE`), which have nothing to do
with production capacity. Alternative: deprecate `building_type` in favour
of "primary capability" immediately. Rejected - `building_type` already
carries meaning unrelated to production (working hours, flavor text,
map/UI display), so collapsing it now would be a much larger, riskier
change than this plan's scope, and the CLAUDE.md planning principles
favour extending over replacing. The plan's docstring intent ("prefer
introducing the capability abstraction before changing `building_type`")
matches this directly.

**c. `granary` and `field_shelter` stay `building_type`-only, not modeled
as capabilities.** Storage (granary) isn't a *production* activity - it
has no worker/labor cap, no `convert_goods` call, nothing a capability
would add. `field_shelter` is already structurally tied to `FieldCrop`
(a `FieldCrop.shelter_building` FK, not a lookup by type) and to land
(`Subzone`), so its "capability" is really "has an attached crop", not a
generic tag. Including them would blur the model without a concrete need
- can be added later if a real use case appears (e.g. a communal
building doubling as storage).

**d. Multiple buildings with the same capability.**
`capacity_services.population_capacity_report` already sums across
`list(population_centre.buildings.filter(building_type="mill"))` for
`workers_present`/`building_count` today - moving to
`filter(capabilities__activity="milling")` preserves exactly this
"sum across every building with the capability" semantic with no new
allocation logic needed. Rejected alternative: making the report pick
a single "primary" building per activity - unnecessary, current behaviour
already handles N buildings per role and multi-capability buildings are
just N buildings potentially overlapping across roles.

**e. `RoleRequirement.building_type` naming in `planning_services.py`.**
Chosen: rename the field to `activity` (or leave it as-is if the rename
churn isn't worth it) once `EconomicActivity` exists, since
`_recommended_buildings` already returns a building *count*, not a type -
the field was already conceptually "which activity does this recommend
building for," `building_type` was just the closest existing vocabulary
at the time it was written. Low-risk, mechanical, can be folded into
step 2 or done separately - flagged as an open question below rather
than decided outright, since it's a pure rename with no behavioural
stake either way.

---

## 5. Edge cases

- **Building with zero capabilities.** A `residential`/`hall`/`market`
  building has no `BuildingCapability` rows - `capacity_services` queries
  simply return nothing for it, same as today's `building_type` filter
  excluding it. No special-casing needed.
- **Building with the same activity added twice.** Add a
  `UniqueConstraint(fields=["building", "activity"])` on
  `BuildingCapability`, mirroring `GoodsStock`'s
  `uniq_goods_stock_per_building` pattern - prevents duplicate rows
  double-counting a building in `mills = list(...)`-style queries.
- **Backfill migration correctness.** Must map every existing
  `building_type` value that has a production meaning today (`mill` →
  `milling`, `bakery` → `baking`) and explicitly do nothing for types
  that don't (`residential`, `hall`, `market`, `communal`, `inn`,
  `granary`, `field_shelter`) - a reversible data migration, tested by
  running it against a representative fixture (e.g. Ashenford/
  Bramblewick-shaped data) and asserting `population_capacity_report`
  output is byte-identical before/after.
- **`GoodsConversionState` is still per-building, not per-capability.**
  A communal building with both milling and baking capabilities shares
  *one* `GoodsConversionState.last_processed_on` row today
  (`OneToOneField(building)`). If `advance_mill_economy_tick` and
  `advance_bakery_economy_tick` both run against the same building on
  the same day, the second tick to run will find `last_processed_on ==
  today` already set by the first and skip - silently not baking (or
  milling). **This needs to become
  `OneToOneField` → per-(building, activity) before step 3 ships**. Call
  this out explicitly as a required fix, not deferred, since it would
  otherwise be an immediate regression the day a multi-capability
  building exists. Add a `UniqueConstraint(fields=["building",
  "activity"])`-shaped tracking row (or add an `activity` field to
  `GoodsConversionState`) alongside the `BuildingCapability` migration.
- **Workers shared across two capabilities in the same building.**
  `workers_present(building)` counts everyone physically at the building,
  with no split between "here to mill" vs. "here to bake" - a
  multi-capability building's milling *and* baking capacity will both be
  computed from the *same* worker count today (each activity sees the
  full headcount, not a fair share). This double-counts labor across
  activities. Documented as a known, deliberate simplification for this
  plan (see Worker allocation below) - not fixed here, but must be called
  out in `capacity_services`/`tasks.py` docstrings so it isn't mistaken
  for a bug later.
- **Migration reversibility.** The backfill data migration should have a
  working `reverse_code` (delete `BuildingCapability` rows created by the
  forward migration) so `migrate economy <previous>` doesn't dead-end.

---

## 6. Tests

- **New**: `BuildingCapability` model - uniqueness constraint,
  `str()`, cascade delete when a `Building` is deleted.
- **New**: backfill data migration - apply to a fixture with mill/bakery/
  field_shelter/residential buildings, assert the right capability rows
  (and only those) are created.
- **Modify**: `economy/tests/test_capacity_services.py` - existing
  `find_mill`/`find_bakery`-adjacent tests should keep passing unchanged
  (backfill preserves behaviour); add a new test where a single
  `communal`-type building holds both `milling` and `baking`
  capabilities and confirm `population_capacity_report` counts it in
  *both* `milling.building_count` and `baking.building_count`.
- **New**: `economy/tests/test_tasks.py` (or wherever `advance_mill_economy_tick`/
  `advance_bakery_economy_tick` are tested today) - a building with both
  capabilities gets processed by both tasks on the same day (this is the
  test that would have caught the `GoodsConversionState` collision in
  Edge cases above - write it before the fix, watch it fail, then fix).
- **Existing**: `economy_status` output/`test_economy_status`-equivalent
  (if one exists) - extend to assert capabilities print correctly.
- Explicitly **not** covered here (deferred to the worker-allocation
  follow-up): any test asserting labor is split fairly between two
  capabilities on the same building - that behaviour doesn't exist yet.

---

## 7. Risks

- Forgetting the `GoodsConversionState` per-building limitation (Edge
  cases above) is the single most likely mistake - it's easy to add
  `BuildingCapability` and update the query filters without noticing the
  existing idempotency guard silently breaks multi-capability ticking.
- Updating `capacity_services` queries but forgetting `economy/tasks.py`'s
  separate `Building.objects.filter(building_type="mill")` /
  `"bakery"` queries (they don't currently go through
  `capacity_services.find_mill`/`find_bakery` for the *iteration* loop,
  only for cross-references like `find_granary`/`find_mill` inside the
  loop body) - both call sites need to move together or the tick tasks
  and the diagnostic report will disagree about which buildings are
  active.
- Writing the backfill migration as a schema-only migration and forgetting
  the data migration, leaving every existing village with zero
  capabilities post-deploy (a total regression, not just Ashenford-style
  partial loss).
- Over-scoping into worker allocation ("while I'm here, let me also split
  workers per-capability") - explicitly out of scope per the prompt;
  resist doing it as part of this plan.

---

## 8. Open questions

- Should `RoleRequirement.building_type` in `planning_services.py` be
  renamed to `activity` now, or left for a later cleanup? (Design
  decision e - low stakes, purely mechanical either way.)
- Should `BuildingCapability` support a per-capability enabled/disabled
  toggle now (e.g. temporarily disable milling at a building without
  deleting the row), or is delete-the-row sufficient until a real need
  appears? Leaning toward deferring - no current caller needs it.
- Is `GoodsConversionState` best fixed by adding an `activity` field
  (simple, but changes its uniqueness semantics) or by introducing a
  separate per-activity idempotency row that reuses the existing model
  shape? Needs a decision before step 3 ships, not before step 1.
- Should the backfill migration also handle any *manually created*
  buildings in existing dev/staging data that have a non-standard
  `building_type` (e.g. hand-edited via admin) - worth a quick data audit
  (`economy_status` or a DB query) on staging before writing the migration,
  not just reasoning from the model code.

---

## Recommended first step

**Step 1 alone**: add the `EconomicActivity` vocabulary, the
`BuildingCapability` model, its migration, and the backfill data
migration - with no callers changed yet. This is the smallest reviewable
PR that establishes the abstraction, is fully additive (zero behaviour
change, verifiable by re-running `economy_status` before/after and diffing
output), and unblocks every later step without committing to the riskier
`GoodsConversionState` fix or the tasks.py/capacity_services query changes
in the same PR. It also gives a concrete place (the backfill migration) to
validate the `EconomicActivity` naming and mapping against real
Ashenford/Bramblewick-shaped data before anything depends on it.
