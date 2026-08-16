"""
Decide who lives together and how they're related, for
locations.generate_characters to turn into actual Character rows.

A "household" here is a social/living unit, not necessarily a family - it
may be a conventional family (partners + children), a single adult, or a
group of unrelated roommates. It deliberately has no model of its own
(no Family table): family-shaped households are expressed with the existing
CharacterRelationship types (MARRIAGE, PARENT_CHILD); non-family households
(roommates, single adults) just have members with no relationship between
them at all.

This module only decides who exists and how they're related to each other -
never which building they live in. household_member_ages runs before any
Character row exists (it works in plain (age, role) pairs), and
create_household_relationships takes real Characters after
generate_characters.py has created them. Housing assignment is a separate,
unrelated step (see generate_characters.py's per-building capacity slots
and place_characters.py) - a household's members are not currently placed
together.
"""

import random

from character.models import RelationshipRole, RelationshipType
from character.services import relationship_services

ADULT_AGE_RANGE = (18, 65)
CHILD_AGE_RANGE = (0, 17)

# How much older a parent must/may be than their child.
PARENT_CHILD_AGE_GAP_RANGE = (18, 45)

FAMILY_ADULT_COUNT_RANGE = (1, 2)
FAMILY_CHILDREN_COUNT_RANGE = (0, 4)
ROOMMATES_COUNT_RANGE = (2, 4)

FAMILY = "family"
SINGLE_ADULT = "single_adult"
ROOMMATES = "roommates"

# Weighted so most households are families, with single adults and
# roommate groups filling out the rest - deliberately simple for a first
# version, not tuned against any real demographic target.
HOUSEHOLD_TYPE_WEIGHTS = {
    FAMILY: 0.55,
    SINGLE_ADULT: 0.30,
    ROOMMATES: 0.15,
}


def _random_child_age(parent_age: int) -> int:
    """
    A plausible child age given a parent's age - within CHILD_AGE_RANGE,
    and within PARENT_CHILD_AGE_GAP_RANGE of parent_age where the two
    ranges overlap. When an older parent's gap range would imply a child
    past CHILD_AGE_RANGE's ceiling, falls back to the oldest age
    CHILD_AGE_RANGE still allows, rather than producing an impossible age.
    """
    min_gap, max_gap = PARENT_CHILD_AGE_GAP_RANGE
    lo = max(CHILD_AGE_RANGE[0], parent_age - max_gap)
    hi = min(CHILD_AGE_RANGE[1], parent_age - min_gap)
    if lo > hi:
        lo = hi
    return random.randint(lo, hi)


def household_member_ages(remaining_budget: int) -> list[tuple[int, str]]:
    """
    One household's worth of (age, role) pairs - role is "parent", "child",
    or "adult" (single_adult/roommates: no family structure implied,
    consumed by create_household_relationships to know who to leave
    unrelated). Always sized to fit within remaining_budget (the number of
    characters still left to generate for the centre) so a caller building
    up a centre's population one household at a time can hit an exact
    total without an oversized last household overshooting it.
    """
    if remaining_budget <= 1:
        return [(random.randint(*ADULT_AGE_RANGE), "adult")]

    household_type = random.choices(
        list(HOUSEHOLD_TYPE_WEIGHTS), weights=list(HOUSEHOLD_TYPE_WEIGHTS.values())
    )[0]

    if household_type == SINGLE_ADULT:
        return [(random.randint(*ADULT_AGE_RANGE), "adult")]

    if household_type == ROOMMATES:
        count = min(random.randint(*ROOMMATES_COUNT_RANGE), remaining_budget)
        return [(random.randint(*ADULT_AGE_RANGE), "adult") for _ in range(count)]

    adult_count = min(random.randint(*FAMILY_ADULT_COUNT_RANGE), remaining_budget)
    adult_ages = [random.randint(*ADULT_AGE_RANGE) for _ in range(adult_count)]

    max_children = min(FAMILY_CHILDREN_COUNT_RANGE[1], remaining_budget - adult_count)
    child_count = (
        random.randint(FAMILY_CHILDREN_COUNT_RANGE[0], max_children)
        if max_children > 0
        else 0
    )
    youngest_parent_age = min(adult_ages)

    members = [(age, "parent") for age in adult_ages]
    members += [
        (_random_child_age(youngest_parent_age), "child") for _ in range(child_count)
    ]
    return members


def create_household_relationships(members) -> None:
    """
    Create the MARRIAGE (if two parents) and PARENT_CHILD relationships a
    household implies, from (character, role) pairs - real Characters
    zipped against the roles household_member_ages assigned them.
    Roommates/single-adult households have no "parent"/"child" roles, so
    this is a no-op for them.
    """
    parents = [char for char, role in members if role == "parent"]
    children = [char for char, role in members if role == "child"]

    if len(parents) == 2:
        relationship_services.relationship_create(
            RelationshipType.MARRIAGE,
            [
                (parents[0], RelationshipRole.SPOUSE),
                (parents[1], RelationshipRole.SPOUSE),
            ],
        )

    for parent in parents:
        for child in children:
            child.add_parent(parent, variant="biological")
