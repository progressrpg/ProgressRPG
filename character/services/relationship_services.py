from __future__ import annotations

import logging

from django.core.exceptions import ValidationError
from django.db import transaction

logger = logging.getLogger("general")
logger_errors = logging.getLogger("errors")


@transaction.atomic
def relationship_create(relationship_type, members, variant=""):
    """
    Create a CharacterRelationship of `relationship_type` with `members` (an
    iterable of (character, role) pairs) and validate that the finished
    relationship meets every role's minimum participant count.

    This whole-structure check is what individual CharacterRelationshipMembership
    saves can't do on their own (they're created one at a time, so a
    relationship is often transiently incomplete mid-construction) - this is
    the sanctioned, all-or-nothing way to build a relationship; the
    transaction rolls back if the finished structure is invalid.
    """
    from character.models import (
        CharacterRelationship,
        CharacterRelationshipMembership,
        RelationshipRole,
        RelationshipType,
        RELATIONSHIP_SPECS,
    )

    relationship_type = RelationshipType(relationship_type)
    spec = RELATIONSHIP_SPECS[relationship_type]

    relationship = CharacterRelationship.objects.create(
        relationship_type=relationship_type, variant=variant
    )

    counts: dict[RelationshipRole, int] = {}
    for character, role in members:
        role = RelationshipRole(role)
        CharacterRelationshipMembership.objects.create(
            relationship=relationship, character=character, role=role
        )
        counts[role] = counts.get(role, 0) + 1

    missing = [
        role.value
        for role, (min_count, _max_count) in spec.roles.items()
        if counts.get(role, 0) < min_count
    ]
    if missing:
        raise ValidationError(
            f"{relationship_type} relationship is missing required role(s): "
            f"{', '.join(missing)}."
        )

    return relationship


def relationship_get_related_characters(character, relationship_type, role=None):
    """
    Other characters sharing a `relationship_type` relationship with
    `character`, optionally restricted to those holding `role` in it.
    """
    from character.models import Character

    filters = {
        "characterrelationshipmembership__relationship__relationship_type": relationship_type,
        "characterrelationshipmembership__relationship__characters": character,
    }
    if role is not None:
        filters["characterrelationshipmembership__role"] = role

    return Character.objects.filter(**filters).exclude(pk=character.pk).distinct()


def relationship_get_parents(character):
    from character.models import RelationshipRole, RelationshipType

    return relationship_get_related_characters(
        character, RelationshipType.PARENT_CHILD, role=RelationshipRole.PARENT
    )


def relationship_get_children(character):
    from character.models import RelationshipRole, RelationshipType

    return relationship_get_related_characters(
        character, RelationshipType.PARENT_CHILD, role=RelationshipRole.CHILD
    )


def relationship_get_siblings(character):
    from character.models import RelationshipType

    return relationship_get_related_characters(character, RelationshipType.SIBLING)


def relationship_get_relationships_of_type(character, relationship_type):
    from character.models import CharacterRelationship

    return CharacterRelationship.objects.filter(
        relationship_type=relationship_type, characters=character
    ).distinct()


def relationship_get_household_members(character):
    """
    `character`'s MARRIAGE/PARENT_CHILD relationship partners (the types
    household_services.create_household_relationships creates - see
    locations/management/commands/generate_characters.py), each as a dict
    with the other character, the relationship's type, and *their* role in
    it - `household_relationship_label` needs their role (not `character`'s
    own) to know whether e.g. a PARENT_CHILD relationship makes them a
    parent or a child of `character`.
    """
    from character.models import CharacterRelationship, RelationshipType

    relationships = (
        CharacterRelationship.objects.filter(
            relationship_type__in=[
                RelationshipType.MARRIAGE,
                RelationshipType.PARENT_CHILD,
            ],
            characters=character,
        )
        .prefetch_related("characterrelationshipmembership_set__character")
        .distinct()
    )

    members = []
    for relationship in relationships:
        memberships = list(relationship.characterrelationshipmembership_set.all())
        if not any(m.character_id == character.id for m in memberships):
            continue
        for membership in memberships:
            if membership.character_id == character.id:
                continue
            members.append(
                {
                    "character": membership.character,
                    "relationship_type": relationship.relationship_type,
                    "other_role": membership.role,
                }
            )
    return members


# Gendered labels for the two relationship types household generation
# actually produces - keyed by the *other* character's sex (Character.
# SexChoices), since "husband"/"son" etc. describe them, not `character`.
_MARRIAGE_LABELS = {"Male": "husband", "Female": "wife"}
_PARENT_LABELS = {"Male": "father", "Female": "mother"}
_CHILD_LABELS = {"Male": "son", "Female": "daughter"}


def household_relationship_label(relationship_type, other_role, other_sex) -> str:
    """
    Human-readable label for the *other* member of one of `character`'s
    household relationships (relationship_get_household_members above),
    e.g. "husband"/"mother"/"daughter" - falls back to a generic word for a
    sex of "Other" or any relationship_type/role combination not covered
    (defensive only; the two types this is actually called for are always
    MARRIAGE/SPOUSE or PARENT_CHILD/PARENT|CHILD).
    """
    from character.models import RelationshipRole, RelationshipType

    if relationship_type == RelationshipType.MARRIAGE:
        return _MARRIAGE_LABELS.get(other_sex, "spouse")

    if relationship_type == RelationshipType.PARENT_CHILD:
        if other_role == RelationshipRole.PARENT:
            return _PARENT_LABELS.get(other_sex, "parent")
        if other_role == RelationshipRole.CHILD:
            return _CHILD_LABELS.get(other_sex, "child")

    return str(relationship_type).replace("_", " ")


def relationship_get_family_groups(characters):
    """
    Map each character's id to a group key such that characters connected via
    PARENT_CHILD or SIBLING relationships - directly or transitively (e.g.
    grandparent -> parent -> child) - share the same key. A character with no
    such relationships gets a singleton group keyed by their own id.

    Computed via union-find over a single bulk query, so callers that need
    family grouping across many characters (e.g. placement logic) don't have
    to query the relationship graph once per character.
    """
    from character.models import CharacterRelationship, RelationshipType

    character_ids = {c.id for c in characters}
    parent = {cid: cid for cid in character_ids}

    def find(cid):
        while parent[cid] != cid:
            parent[cid] = parent[parent[cid]]
            cid = parent[cid]
        return cid

    def union(a, b):
        root_a, root_b = find(a), find(b)
        if root_a != root_b:
            parent[root_a] = root_b

    relationships = (
        CharacterRelationship.objects.filter(
            relationship_type__in=[
                RelationshipType.PARENT_CHILD,
                RelationshipType.SIBLING,
            ],
            characters__in=character_ids,
        )
        .prefetch_related("characterrelationshipmembership_set")
        .distinct()
    )

    for relationship in relationships:
        member_ids = [
            membership.character_id
            for membership in relationship.characterrelationshipmembership_set.all()
            if membership.character_id in character_ids
        ]
        for other_id in member_ids[1:]:
            union(member_ids[0], other_id)

    return {cid: find(cid) for cid in character_ids}
