# Plan: Size new villages to minimum-viable production capacity, with link-scaled worker output

## Context

Goal (from the user, verbatim intent): a freshly-generated population
centre should start with just enough production capacity to feed its
residents - not comfortably staffed, not starving. As players link to
characters and play, `link_points` accrue, and that should raise the
linked character's work output, visibly pulling the village's production
capacity from "barely enough" toward "comfortable" - the mechanism that
makes linking a player to a character matter economically. This is
**explicitly not** about `PopulationCentre.state` (the existing
`total_ap_earned`/`village_points`-driven Struggling/Recovering/Stable/
Thriving property) - that stays untouched and is being worked on
separately. Using `link_points` (not `Character.level`/`total_ap_earned`)
keeps the two signals genuinely distinct rather than double-counting the
same number for two different UI/economy purposes.

This builds directly on the already-shipped `BuildingCapability` work
(`.claude/plans/building-capabilities-plan.md`, steps 1-3): a village no
longer needs one dedicated building per production role, so a small
village can size a single multi-capability building instead of silently
missing a role (the original Ashenford bug).

Two existing pieces already point at this goal but aren't wired together:
- `economy/services/planning_services.py.settlement_plan()` already
  computes "how many workers/buildings does a population need" from a
  resident count - built for exactly this, per its own docstring, but
  never called by the generation pipeline.
- `locations/services/population_estimation.py`'s docstring literally
  says: *"Feeding population_capacity() into
  planning_services.settlement_plan(population=...) to size economy
  infrastructure ... is not wired up yet - a separate follow-up."* This
  plan is that follow-up.

**Explicitly out of scope** (per direct answers already given):
- `PopulationCentre.state` / `village_points` - untouched.
- `locations/management/commands/assign_workers.py` (WORK assignment) -
  stays as-is: every non-residential building gets a flat random 2-3
  workers, independent of role/demand. **This is a real tension, not
  ignored** - see Risks below, since it means building/capability sizing
  alone cannot *guarantee* a "just enough" starting state while worker
  *counts* stay demand-blind. Flagged as a required follow-up.

---

## 1. High-level strategy

Three additive pieces, each independently shippable:

**A. Link-scaled worker productivity.** Replace the flat headcount in the
capacity-consuming call sites of `capacity_services.workers_present()`
with a productivity-weighted sum, where each present character
contributes `1 + f(total_link_points)` instead of a flat `1`. `f` is a
diminishing-returns curve (not linear - `link_points` is cumulative and
unbounded, so a flat linear multiplier would let productivity grow
without limit forever). An unlinked NPC has zero `link_points` and
contributes exactly `1` - the existing baseline behaviour is unchanged
until a character actually gets linked and played.

**B. Wire `population_estimation` into `settlement_plan`.** Give
`settlement_plan()` a population figure at generation time (before real
residents exist) via `population_estimation.population_capacity()` /
`estimate_population_from_footprint_areas()`, so building/capability
counts are sized to the settlement's actual scale instead of the
generator's current fixed lists (`SPECIAL_BUILDINGS` in
`generate_villages.py`, `SPECIAL_BUILDING_TYPES` in `watabou_import.py`).

**C. Generate `BuildingCapability` rows from the plan, not a fixed type
list.** `generate_villages.py`/`watabou_import.py` stop hardcoding "one
granary, one inn, one mill, one bakery" and instead ask
`settlement_plan()` how many milling/baking/farming-supporting buildings
are recommended, assigning capabilities accordingly - including packing
multiple capabilities onto one building (e.g. `communal`) for small
villages, closing the original Ashenford gap by construction instead of
by luck of import ordering.

---

## 2. Files likely to change

- `character/models/character.py` - **existing**. Add a
  `Character.total_link_points` property (mirrors the existing
  `Player.total_link_points` at `users/models.py:439`), summing
  `PlayerCharacterLink.total_link_points(self.links.all())` over every
  link the character has ever had (active or historical) - the natural
  input to the productivity formula.
- `economy/services/capacity_services.py` - **existing**. `workers_present`
  returns a plain count today and stays as-is (still needed for pure
  presence checks). Add a new weighted function (e.g.
  `worker_capacity_present(building)`) used wherever a headcount
  currently feeds a `capacity_per_day`/labor-cap calculation.
- `economy/constants.py` - **existing**. Add the productivity curve
  constant(s) (e.g. `LINK_POINTS_PRODUCTIVITY_SCALE`,
  `MAX_PRODUCTIVITY_BONUS`), following the existing pattern of every
  other economy constant being a single named, commented, reasoned value.
- `economy/tasks.py` - **existing**. `_harvest`, `advance_mill_economy_tick`,
  `advance_bakery_economy_tick` swap `workers_present(...)` for the new
  weighted function where it feeds a labor-cap calculation (presence-only
  checks elsewhere are unaffected).
- `economy/services/planning_services.py` - **existing, likely no
  change**. Already population-driven; step B only changes *what
  population figure* generation code passes in, not this service.
- `locations/services/population_estimation.py` - **existing**. Docstring
  already anticipates this; likely just gains the actual call site
  elsewhere, not internal changes.
- `locations/services/watabou_import.py` - **existing**.
  `_assign_building_types`/`SPECIAL_BUILDING_TYPES` replaced by
  capability-aware sizing from `settlement_plan`.
- `locations/management/commands/generate_villages.py` - **existing**.
  `SPECIAL_BUILDINGS` fixed list replaced the same way.
- New tests: `economy/tests/test_capacity_services.py` (productivity
  weighting), `character/tests/*` (`total_link_points`),
  `locations/tests/test_watabou_import.py` /
  `test_generate_villages.py`-equivalent (capability-aware generation).

---

## 3. Implementation plan

Independent, sequential PRs:

1. **`Character.total_link_points` property.** Small, isolated, no
   economy-side change yet - just exposes the input the productivity
   formula needs.
2. **Link-scaled worker capacity.** Add the productivity curve to
   `economy/constants.py` and the weighted-sum function to
   `capacity_services.py`. Wire it into `economy/tasks.py`'s three
   conversion ticks and `population_capacity_report`. No generation
   changes yet - this alone makes existing villages' capacity respond to
   linked characters playing.
3. **Wire population into settlement_plan at generation time.** Add a
   call path from `generate_villages.py`/`watabou_import.py` to
   `population_estimation` + `settlement_plan`, without yet changing what
   buildings get created - just compute and log/print the recommended
   plan, to validate the numbers against real village files before
   changing generation behaviour.
4. **Generate capabilities from the plan.** Replace the fixed
   `SPECIAL_BUILDINGS`/`SPECIAL_BUILDING_TYPES` allocation with
   `settlement_plan`-driven capability assignment - including the
   multi-capability packing case for small villages.
5. **(Flagged, not built here) Make `assign_workers.py` demand-aware.**
   Needed to actually *guarantee* the "struggling at spawn" outcome end
   to end - called out as the next real follow-up once 1-4 land, not
   bundled in here per the existing scope boundary.

---

## 4. Design decisions

**a. Add a new weighted-capacity function vs. changing `workers_present`
in place.** Chosen: add alongside (e.g. `worker_capacity_present`), don't
change `workers_present`'s return type. Alternative: make
`workers_present` itself productivity-weighted. Rejected -
`workers_present` is also used for pure presence checks (deciding
*whether* production happens at all, not *how much*); silently turning
its return value from "headcount" into "weighted capacity units" would
be a subtle unit-confusion bug risk for any caller doing `if
workers_present(building):`. A differently-named function makes the unit
explicit at every call site.

**b. `link_points`-based, diminishing-returns curve, not linear.**
`link_points` accrues daily (`days_linked * 20 + login_points +
time_points`, see `PlayerCharacterLink.link_points`) with no ceiling, so
a flat linear multiplier (`1 + link_points * k`) would make a
long-linked character's output grow forever, eventually dwarfing every
other constant in the economy - a balance and realism problem (a single
baker shouldn't out-produce ten fresh workers after a year). Recommend a
capped or diminishing-returns shape instead (e.g. `1 +
min(link_points / SCALE, MAX_BONUS)`, or a square-root curve) so
early linking gives a clear, visible boost and further play has
naturally shrinking marginal effect. Exact shape/constants are a
balancing question, not decided here (see Open Questions) - but "must
not be unbounded linear" is a firm constraint from this reasoning alone.

**c. Sum `link_points` over every link a character has ever had, not just
the active one.** Chosen: `Character.total_link_points` mirrors
`Player.total_link_points`'s existing pattern of summing across all
links (`self.links.all()`), not filtering to `is_active=True`. Alternative:
only count the character's current active link, dropping accrued
productivity the moment a player unlinks. Rejected - would make
unlinking actively punish the village (a sudden capacity drop) rather
than just stopping further growth, which reads as a harsh, arguably
unintended consequence; retaining past investment while a character is
between links is the friendlier default and mirrors how `link_points`
itself already behaves as a permanent, cumulative figure once earned.

**d. Multi-capability packing for small villages.** Reuse
`BuildingCapability`'s existing per-building multiplicity - a
`settlement_plan.milling.recommended_buildings == 1` and
`baking.recommended_buildings == 1` for a small village both resolve to
capabilities added to the *same* generated building (e.g. `communal`)
rather than two half-empty dedicated buildings, matching the user's
original framing ("small village: communal building -> milling +
baking"). Alternative: always generate one dedicated building per role
regardless of size. Rejected - defeats the purpose of the capability
work and reproduces the original small-village building-count pressure
that caused the Ashenford gap in the first place.

---

## 5. Edge cases

- **Zero starting population.** `settlement_plan(population=0)` already
  returns `milling`/`baking`/`granaries` recommended at a floor of 1 (see
  existing `planning_services` tests) - generation must still create at
  least minimal capability coverage for a population-0 village, not skip
  entirely.
- **`workers_present` vs. the new weighted function returning
  inconsistent "is anyone here" signals.** Needs a clear contract (e.g.
  weighted function returns exactly `0` iff headcount is `0`, since every
  present character contributes at least `1`) so callers can't get a
  false "someone's working" signal from an empty building, and an empty
  building never accidentally produces a nonzero weighted value.
- **`assign_workers.py` still not demand-aware (see Risks).** Concretely:
  after this plan, a tiny village could get a `communal` building sized
  by `settlement_plan` for exactly 1 milling + 1 baking worker, but
  `assign_workers.py` still hands it 2-3 random workers regardless -
  overshooting "struggling" on day one. Document this explicitly rather
  than let it look silently resolved.
- **Existing villages (already generated) don't retroactively resize.**
  This plan only changes generation for *new* villages; nothing here
  touches already-seeded population centres' existing buildings/
  capabilities (consistent with how the `BuildingCapability` backfill
  migration handled existing data - additive, not retroactive resizing).
  Existing characters do, however, immediately benefit from step 2's
  productivity weighting the moment it ships, since it reads
  `total_link_points` live.

---

## 6. Tests

- **New**: `Character.total_link_points` - sums across multiple links
  (active and historical/unlinked), zero for a never-linked character.
- **New**: productivity-weighted capacity - a character with nonzero
  `link_points` contributes more than an unlinked character to
  `capacity_per_day`; the bonus is capped/diminishing, not unbounded
  (assert the curve's ceiling behaviour, not just "more is more"),
  formula-derived from the new constants (mirroring
  `test_capacity_services.py`'s existing "never hardcode a literal"
  convention).
- **New**: `settlement_plan`-driven generation - a small imported village
  (few buildings) ends up with both milling and baking capabilities on
  one building rather than missing one; a larger village gets dedicated
  buildings per role, matching `recommended_buildings` from the plan.
- **Modify**: existing `generate_villages`/`watabou_import` tests
  (`test_watabou_import.py`'s `test_leftover_after_every_special_type_
  falls_back_to_residential` etc.) will need to change or be replaced,
  since the fixed-order special-type allocation they test is exactly
  what's being removed.
- **Not covered here** (deferred with `assign_workers.py`): any test
  asserting a freshly-generated village's *actual* worker headcount
  matches its `settlement_plan` recommendation end-to-end - that
  guarantee doesn't exist until `assign_workers.py` becomes demand-aware.

---

## 7. Risks

- **The "struggling at spawn" outcome isn't actually guaranteed by this
  plan alone.** Without also making `assign_workers.py` demand-aware,
  sizing buildings/capabilities correctly doesn't control how many
  workers actually get assigned to them. The user's scope answer keeps
  this out of the current plan deliberately - worth re-confirming before
  implementation starts, since it means steps 3-4 alone won't visibly
  deliver the stated goal without step 5 eventually following.
- **Unbounded productivity if the curve is implemented as linear by
  mistake** - the single most important constraint from design decision
  (b) to not lose during implementation; write the capped-behaviour test
  before the implementation, not after.
- Conflating "productivity multiplier" (step 2) with "worker count"
  (steps 3-4) in the same PR would make it hard to isolate which change
  affected a given capacity number during testing/balancing - keep them
  as the separate steps laid out above.

---

## 8. Open questions

- Exact productivity curve shape and constants (`SCALE`, `MAX_BONUS` or
  equivalent) need real playtesting/balancing, not just a
  plausible-sounding default - flag for a balance pass once visible,
  consistent with how every other economy constant in this codebase is
  annotated as approximate pending real tuning.
- Should the productivity bonus apply per-capability (a character could
  theoretically be more "trained" at baking than milling) or uniformly
  per-character regardless of which building they're assigned to?
  Recommend uniform-per-character for this plan - per-capability skill
  is a much larger character-progression feature on its own.
- Should `assign_workers.py` becoming demand-aware be scoped as the
  *immediate* next plan after this one, given it's required to actually
  deliver the user's stated goal end-to-end?
