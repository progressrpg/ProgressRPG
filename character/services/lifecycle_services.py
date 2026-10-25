from __future__ import annotations

import logging
from random import randint
from django.utils import timezone

logger = logging.getLogger("general")
logger_errors = logging.getLogger("errors")


def relationship_adjust_strength(relationship, amount: int) -> None:
    relationship.strength = max(min(relationship.strength + amount, 100), -100)
    relationship.save()


def relationship_log_event(relationship, event) -> None:
    relationship.history.setdefault("events", []).append(event)
    relationship.save()


def get_age(instance) -> int:
    if instance.birth_date is None:
        return 0
    return (timezone.now().date() - instance.birth_date).days


def die(instance) -> None:
    instance.death_date = timezone.now().date()
    instance.save(update_fields=["death_date"])
    journey = instance.current_journey
    if journey:
        journey.cancel()


def is_alive(instance) -> bool:
    return instance.death_date is None


def get_romantic_partners(instance):
    from character.models import RelationshipType
    from character.services import relationship_services

    return relationship_services.relationship_get_related_characters(
        instance, RelationshipType.ROMANTIC
    )


def is_fertile(instance) -> bool:
    return instance.fertility > 0


def can_reproduce_with(instance, partner) -> bool:
    from character.models import Character

    if instance.fertility <= 0 or partner.fertility <= 0:
        return False
    if (
        instance.sex == Character.SexChoices.MALE
        and partner.sex == Character.SexChoices.MALE
        or instance.sex == Character.SexChoices.FEMALE
        and partner.sex == Character.SexChoices.FEMALE
    ):
        return False
    return True


def attempt_pregnancy(instance) -> bool:
    romantic_partners = get_romantic_partners(instance)

    for partner in romantic_partners:
        if can_reproduce_with(instance, partner):
            if is_fertile(instance) and not instance.is_pregnant:
                start_pregnancy(instance, partner)
                return True
    return False


def start_pregnancy(instance, partner) -> None:
    instance.is_pregnant = True
    instance.pregnancy_start_date = timezone.now().date()
    instance.pregnancy_partner = partner

    instance.save()


def handle_childbirth(instance) -> None:
    from character.models import Character

    child_name = f"Child of {instance.name}"
    child = Character.objects.create(
        given_name=child_name,
        birth_date=timezone.now().date(),
        sex=(
            Character.SexChoices.MALE
            if randint(0, 1) == 0
            else Character.SexChoices.FEMALE
        ),
    )

    child.add_parent(instance, variant="biological")
    if instance.pregnancy_partner:
        child.add_parent(instance.pregnancy_partner, variant="biological")
    child.save()


def handle_miscarriage(instance) -> None:
    instance.is_pregnant = False
    instance.pregnancy_start_date = None
    instance.save()


def get_miscarriage_change(instance) -> float:
    chance = 0.05
    if get_age(instance) > (40 * 365):
        chance += 0.10
    return round(chance, 5)
