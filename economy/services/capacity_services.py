"""
Population-driven economy capacity: how much a population centre's
residents demand in bread/flour/wheat per day, and how much its bakery/
mill/field workforce can actually produce at current staffing.

`workers_present`/`find_granary`/`find_mill`/`find_bakery`/
`daily_bread_demand`/`daily_flour_demand` are shared with the daily economy
ticks in economy/tasks.py (moved here rather than duplicated) - both the
simulation and this module need the same "who's actually present" and
"how much does this village eat" logic. `population_capacity_report`
builds on top of them for the economy_status diagnostic command.
"""

from dataclasses import dataclass

from economy.constants import (
    BREAD_PER_CHARACTER_DAILY_CONSUMPTION,
    FLOUR_TO_BREAD_RATIO,
    LINK_POINTS_PRODUCTIVITY_SCALE,
    MAX_PRODUCTIVITY_BONUS,
    PER_WORKER_DAILY_BAKING_CAPACITY,
    PER_WORKER_DAILY_CAPACITY,
    PER_WORKER_DAILY_MILLING_CAPACITY,
    WHEAT_TO_FLOUR_RATIO,
)


def workers_present(building):
    """
    Characters physically standing at `building` right now (not mid-move) -
    the same "must actually show up" presence check every labor-capped
    economy tick (harvest/mill/bake) uses to cap production.
    """
    from character.models import Character

    return Character.objects.filter(
        current_node__building=building, is_moving=False
    ).count()


def _productivity_bonus(character):
    return min(
        character.total_link_points / LINK_POINTS_PRODUCTIVITY_SCALE,
        MAX_PRODUCTIVITY_BONUS,
    )


def worker_capacity_present(building):
    """
    Weighted labor capacity physically present at `building` right now -
    like workers_present, but each present character contributes
    1 + _productivity_bonus(character) instead of a flat 1, so a linked
    character with accrued total_link_points produces more than an
    unlinked NPC (which contributes exactly 1, unchanged from today's
    behaviour). Zero iff workers_present(building) is zero, so callers that
    branch on "is anyone here" can safely use either function.
    """
    from character.models import Character

    characters = Character.objects.filter(
        current_node__building=building, is_moving=False
    )
    return sum(1 + _productivity_bonus(character) for character in characters)


def find_granary(population_centre):
    if population_centre is None:
        return None
    return (
        population_centre.buildings.filter(building_type="granary")
        .order_by("id")
        .first()
    )


def find_mill(population_centre):
    if population_centre is None:
        return None
    return (
        population_centre.buildings.filter(capabilities__activity="milling")
        .order_by("id")
        .first()
    )


def find_bakery(population_centre):
    if population_centre is None:
        return None
    return (
        population_centre.buildings.filter(capabilities__activity="baking")
        .order_by("id")
        .first()
    )


def daily_bread_demand_for_population(resident_count):
    """
    Pure resident-count -> bread demand, with no PopulationCentre
    dependency - shared with economy.services.planning_services, which
    needs the same formula for a raw population size that has no
    PopulationCentre yet.
    """
    return resident_count * BREAD_PER_CHARACTER_DAILY_CONSUMPTION


def daily_flour_demand_for_population(resident_count):
    return daily_bread_demand_for_population(resident_count) / FLOUR_TO_BREAD_RATIO


def daily_wheat_demand_for_population(resident_count):
    """
    Wheat that must be milled per day to keep flour demand covered - the
    inverse of WHEAT_TO_FLOUR_RATIO, mirroring how
    daily_flour_demand_for_population inverts FLOUR_TO_BREAD_RATIO.
    """
    return daily_flour_demand_for_population(resident_count) / WHEAT_TO_FLOUR_RATIO


def daily_bread_demand(population_centre):
    if population_centre is None:
        return 0.0
    return daily_bread_demand_for_population(population_centre.resident_count)


def daily_flour_demand(population_centre):
    if population_centre is None:
        return 0.0
    return daily_flour_demand_for_population(population_centre.resident_count)


def daily_wheat_demand(population_centre):
    if population_centre is None:
        return 0.0
    return daily_wheat_demand_for_population(population_centre.resident_count)


@dataclass
class CapacityLine:
    """
    One production role (farming/milling/baking) in a population capacity
    report: how many buildings and physically-present workers back it, the
    resulting labor-capped output per day (in the units of the good it
    produces - wheat for farming, flour for milling, bread for baking), and
    the population's daily demand for that same good.

    `capacity_per_day` is a pure labor-cap estimate (workers * per-worker
    constant, converted through the relevant yield ratio where the role
    consumes an input good) - it deliberately ignores storage headroom and
    available input stock, unlike the real conversion tick (see
    economy.conversion.convert_goods), since this is meant to answer "does
    this village have enough *workforce*", not simulate a specific day.
    """

    building_count: int
    workers_present: int
    capacity_per_day: float
    demand_per_day: float

    @property
    def surplus_per_day(self):
        return self.capacity_per_day - self.demand_per_day

    @property
    def is_shortfall(self):
        return self.surplus_per_day < 0


@dataclass
class PopulationCapacityReport:
    population_centre: object
    resident_count: int
    daily_bread_demand: float
    daily_flour_demand: float
    daily_wheat_demand: float
    farming: CapacityLine
    milling: CapacityLine
    baking: CapacityLine


def population_capacity_report(population_centre):
    """
    Build a full needs-vs-capacity report for one population centre: daily
    bread/flour/wheat demand from its resident count, against labor-capped
    farming/milling/baking capacity from its current buildings and present
    workers. Read-only - queries current state, doesn't simulate or persist
    anything (see economy_forecast's advance_*_economy_tick calls for the
    actual simulation).
    """
    from economy.models import FieldCrop

    bread_demand = daily_bread_demand(population_centre)
    flour_demand = daily_flour_demand(population_centre)
    wheat_demand = daily_wheat_demand(population_centre)

    field_shelters = list(
        population_centre.buildings.filter(building_type="field_shelter")
    )
    field_count = FieldCrop.objects.filter(shelter_building__in=field_shelters).count()
    farming_workers = sum(workers_present(shelter) for shelter in field_shelters)
    farming_capacity = sum(
        worker_capacity_present(shelter) for shelter in field_shelters
    )
    farming = CapacityLine(
        building_count=field_count,
        workers_present=farming_workers,
        # Harvesting yields wheat directly - no input good/yield ratio.
        # capacity_per_day is weighted by link-scaled productivity
        # (worker_capacity_present), not the raw headcount above.
        capacity_per_day=farming_capacity * PER_WORKER_DAILY_CAPACITY,
        demand_per_day=wheat_demand,
    )

    mills = list(population_centre.buildings.filter(capabilities__activity="milling"))
    milling_workers = sum(workers_present(mill) for mill in mills)
    milling_capacity = sum(worker_capacity_present(mill) for mill in mills)
    milling = CapacityLine(
        building_count=len(mills),
        workers_present=milling_workers,
        # PER_WORKER_DAILY_MILLING_CAPACITY caps grain milled (input); the
        # flour actually produced is that, run through WHEAT_TO_FLOUR_RATIO
        # - see convert_goods, which this mirrors. Weighted by link-scaled
        # productivity (worker_capacity_present), not the raw headcount.
        capacity_per_day=milling_capacity
        * PER_WORKER_DAILY_MILLING_CAPACITY
        * WHEAT_TO_FLOUR_RATIO,
        demand_per_day=flour_demand,
    )

    bakeries = list(population_centre.buildings.filter(capabilities__activity="baking"))
    baking_workers = sum(workers_present(bakery) for bakery in bakeries)
    baking_capacity = sum(worker_capacity_present(bakery) for bakery in bakeries)
    baking = CapacityLine(
        building_count=len(bakeries),
        workers_present=baking_workers,
        # Same shape as milling: PER_WORKER_DAILY_BAKING_CAPACITY caps
        # flour baked (input), FLOUR_TO_BREAD_RATIO yields bread (output).
        # Weighted by link-scaled productivity, not the raw headcount.
        capacity_per_day=baking_capacity
        * PER_WORKER_DAILY_BAKING_CAPACITY
        * FLOUR_TO_BREAD_RATIO,
        demand_per_day=bread_demand,
    )

    return PopulationCapacityReport(
        population_centre=population_centre,
        resident_count=population_centre.resident_count,
        daily_bread_demand=bread_demand,
        daily_flour_demand=flour_demand,
        daily_wheat_demand=wheat_demand,
        farming=farming,
        milling=milling,
        baking=baking,
    )
