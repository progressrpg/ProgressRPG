"""
Population-driven settlement planning: given a population size (either a
PopulationCentre or a raw resident count), what farming/milling/baking
workforce and infrastructure *should* exist to sustain it.

This is prescriptive ("what should exist"), unlike
economy.services.capacity_services ("what's there and staffed right now").
It exists so a future importer change can ask this service to size
infrastructure by population instead of embedding its own hardcoded
ratios (see locations/services/watabou_import.py's
RESIDENTIAL_BUILDING_RATIO-style approach) - the importer itself is not
touched here.

Every demand/workforce figure is derived from economy.constants, not a
hardcoded number, so retuning a constant (e.g. PER_WORKER_DAILY_CAPACITY)
automatically flows through to the recommended plan.
"""

import math
from dataclasses import dataclass

from economy.constants import (
    FLOUR_TO_BREAD_RATIO,
    PER_WORKER_DAILY_BAKING_CAPACITY,
    PER_WORKER_DAILY_CAPACITY,
    PER_WORKER_DAILY_MILLING_CAPACITY,
    SMALL_SETTLEMENT_POPULATION_THRESHOLD,
    WHEAT_TO_FLOUR_RATIO,
)
from economy.services.capacity_services import (
    daily_bread_demand_for_population,
    daily_flour_demand_for_population,
    daily_wheat_demand_for_population,
)


@dataclass
class RoleRequirement:
    """
    One labor role in the farm-mill-bake chain: how much output the
    population demands from it per day, how many workers that takes at
    current per-worker capacity constants, and the buildings recommended
    to house them. Same shape as capacity_services.CapacityLine, but
    prescriptive ("what should exist") rather than diagnostic ("what's
    there and staffed now").
    """

    building_type: str
    demand_per_day: float
    workers_needed: int
    recommended_buildings: int


@dataclass
class SettlementPlan:
    resident_count: int
    daily_bread_demand: float
    daily_flour_demand: float
    daily_wheat_demand: float
    farming: RoleRequirement
    milling: RoleRequirement
    baking: RoleRequirement
    # Storage only - no workforce role (and no capacity sizing) yet, unlike
    # farming/milling/baking. Always recommended, per the "assume every
    # population centre should have grain storage... even if small" rule
    # below.
    recommended_granaries: int
    # Population-driven signal (not a building-slot-scarcity one) for
    # whether a settlement should share one building for milling and
    # baking rather than getting a dedicated building per role - see
    # SMALL_SETTLEMENT_POPULATION_THRESHOLD. Consumers (e.g.
    # watabou_import) still fall back to sharing when there genuinely
    # isn't room for two dedicated buildings, regardless of this flag.
    combine_milling_and_baking: bool


def _workers_needed(demand_per_day, per_worker_capacity, yield_ratio=1.0):
    """
    Inverse of the capacity_per_day formula in
    capacity_services.population_capacity_report (workers * per-worker
    constant * yield ratio, where the ratio is 1.0 for a role - farming -
    whose per-worker constant already yields the output good directly):
    how many workers are needed to clear a given daily demand.
    """
    if demand_per_day <= 0:
        return 0
    return math.ceil(demand_per_day / (per_worker_capacity * yield_ratio))


def _recommended_buildings(workers_needed, always_present):
    """
    How many buildings to recommend for a role, given how many workers it
    needs.

    No per-building worker cap exists yet in the simulation (a mill/
    bakery/field_shelter can host any number of physically-present workers
    - see capacity_services.workers_present), so one building is always
    sufficient to house any number of workers today. This is the single
    spot to change once a real per-building labor cap exists (see
    "communal buildings" / "multiple bakeries or mills in larger
    settlements" in the planning issue) - e.g.
    math.ceil(workers_needed / MAX_WORKERS_PER_BUILDING).

    `always_present` roles (milling, baking) are recommended even with
    zero workers needed, per "assume every population centre should have
    grain storage, milling, and baking even if these are small". Farming
    isn't - it depends on farmland (FieldCrop/Subzone) this service
    doesn't control, so a population with no farming need gets zero
    recommended field shelters.
    """
    floor = 1 if always_present else 0
    return max(floor, 1 if workers_needed > 0 else 0)


def _role_requirement(
    building_type, demand_per_day, per_worker_capacity, yield_ratio, always_present
):
    workers_needed = _workers_needed(demand_per_day, per_worker_capacity, yield_ratio)
    return RoleRequirement(
        building_type=building_type,
        demand_per_day=demand_per_day,
        workers_needed=workers_needed,
        recommended_buildings=_recommended_buildings(workers_needed, always_present),
    )


def _settlement_plan_for_residents(resident_count):
    bread_demand = daily_bread_demand_for_population(resident_count)
    flour_demand = daily_flour_demand_for_population(resident_count)
    wheat_demand = daily_wheat_demand_for_population(resident_count)

    farming = _role_requirement(
        "field_shelter",
        wheat_demand,
        PER_WORKER_DAILY_CAPACITY,
        yield_ratio=1.0,
        always_present=False,
    )
    milling = _role_requirement(
        "mill",
        flour_demand,
        PER_WORKER_DAILY_MILLING_CAPACITY,
        yield_ratio=WHEAT_TO_FLOUR_RATIO,
        always_present=True,
    )
    baking = _role_requirement(
        "bakery",
        bread_demand,
        PER_WORKER_DAILY_BAKING_CAPACITY,
        yield_ratio=FLOUR_TO_BREAD_RATIO,
        always_present=True,
    )

    return SettlementPlan(
        resident_count=resident_count,
        daily_bread_demand=bread_demand,
        daily_flour_demand=flour_demand,
        daily_wheat_demand=wheat_demand,
        farming=farming,
        milling=milling,
        baking=baking,
        recommended_granaries=1,
        combine_milling_and_baking=resident_count
        <= SMALL_SETTLEMENT_POPULATION_THRESHOLD,
    )


def settlement_plan(population_centre=None, population=None):
    """
    Build a SettlementPlan from either a PopulationCentre or a raw
    resident count - exactly one must be given.
    """
    if (population_centre is None) == (population is None):
        raise ValueError(
            "settlement_plan requires exactly one of population_centre or population"
        )
    resident_count = (
        population_centre.resident_count
        if population_centre is not None
        else population
    )
    return _settlement_plan_for_residents(resident_count)
