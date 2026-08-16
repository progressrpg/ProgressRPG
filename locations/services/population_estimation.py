"""
Estimate how many residents a settlement's housing can plausibly support,
from residential building *geometry* alone - no Character rows required.

This is one step further back than economy.services.planning_services:
that layer answers "given a population, what infrastructure should exist";
this layer answers "given the residential buildings that exist (or will),
how big a population do they imply". It exists so a freshly-imported
settlement (see locations/services/watabou_import.py) - which has no real
residents yet at import time - can still get a population figure.

starting_population() is what setup_world.py's pipeline actually uses,
via generate_characters.py, to size a settlement's initial cast instead of a
flat per-building ratio. Feeding population_capacity() into
planning_services.settlement_plan(population=...) to size economy
infrastructure (granary/mill/bakery counts) by the same figure is not
wired up yet - a separate follow-up.
"""

import math
import random

from locations.management.commands.populate_interiors import (
    BUILDING_INTERIORS_PROPORTIONS,
)

# Square metres of sleeping space assumed to house one resident - a shared/
# historical sleeping density (a room sleeps several people), not modern
# one-person-per-bedroom floor space. Every estimate below derives from
# this plus the existing BUILDING_INTERIORS_PROPORTIONS sleeping-space
# split, so retuning either automatically flows through.
SLEEPING_AREA_PER_RESIDENT_SQM = 6.0

# A building's footprint is a visual/architectural shape (Watabou-imported
# footprints in particular run large - single "houses" of 100-500 sqm - see
# watabou_import.py), not a literal floor plan divided cleanly into bunks.
# Treating 100% of the theoretical sleeping-area capacity as occupiable
# overstates household size well past anything plausible; this scales it
# down to one. Tuned so a large imported "house" footprint lands around
# 6-11 residents rather than 17-31.
RESIDENTIAL_OCCUPANCY_FACTOR = 0.35

# Fraction of residential capacity a settlement starts populated to - below
# 1.0 so there's room for growth and player impact, and randomised within
# the range so no settlement starts perfectly optimised.
STARTING_POPULATION_FRACTION_RANGE = (0.4, 0.7)


def _capacity_from_area(footprint_area: float) -> int:
    """
    Core calc both public entry points below delegate to: how many
    residents a residential footprint of this area could sleep, using the
    same "sleeping" proportion of a building's footprint that
    populate_interiors.generate_subspaces would carve out as an
    InteriorSpace - computed analytically so this works before interiors
    (or even a database row) exist.
    """
    sleeping_fraction = BUILDING_INTERIORS_PROPORTIONS["residential"]["sleeping"]
    sleeping_area = footprint_area * sleeping_fraction
    return math.floor(
        sleeping_area / SLEEPING_AREA_PER_RESIDENT_SQM * RESIDENTIAL_OCCUPANCY_FACTOR
    )


def residential_capacity(building) -> int:
    """
    Capacity of one real, saved residential Building. 0 for any other
    building_type, or a Building with no footprint.
    """
    if building.building_type != "residential" or not building.footprint:
        return 0
    return _capacity_from_area(building.footprint.area)


def population_capacity(population_centre) -> int:
    """
    Sum of residential_capacity over every residential Building already
    saved for a PopulationCentre - for settlements with real Building rows.
    Unlike estimate_population_from_footprint_areas below, this needs the
    buildings to already exist and be typed "residential".
    """
    return sum(
        residential_capacity(building)
        for building in population_centre.buildings.filter(building_type="residential")
    )


def estimate_population_from_footprint_areas(footprint_areas: list[float]) -> int:
    """
    Sum of _capacity_from_area over a raw list of footprint areas (square
    metres) - for watabou_import, which has building footprint Polygons
    before any Building row is created (see _assign_building_types, called
    ahead of the Building.objects.create loop), so it has no building_type
    to filter on yet.
    """
    return sum(_capacity_from_area(area) for area in footprint_areas)


def starting_population(population_centre) -> int:
    """
    How many residents a freshly-imported/spawned settlement should start
    with - a fraction of population_capacity, not the full figure, so
    there's room to grow. 0 if the settlement has no residential capacity
    at all.

    Seeded on the capacity value itself (not population_centre.id/.name):
    those are re-assigned on every world rebuild (autoincrement PK; import
    picks a random unused name), so they don't survive a reimport, but
    capacity is a pure function of the imported geometry - seeding on it
    means the same source village file always yields the same starting
    population, even across a full setup_world rerun.
    """
    capacity = population_capacity(population_centre)
    if capacity <= 0:
        return 0
    rng = random.Random(capacity)
    fraction = rng.uniform(*STARTING_POPULATION_FRACTION_RANGE)
    return max(1, math.floor(capacity * fraction))
