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


def lifecycle_get_age(instance) -> int:
    return (timezone.now().date() - instance.birth_date).days


def lifecycle_die(instance) -> None:
    instance.death_date = timezone.now().date()
    instance.save(update_fields=["death_date"])
    instance.cancel_journey()


def lifecycle_is_alive(instance) -> bool:
    return instance.death_date is None


def lifecycle_get_romantic_partners(instance):
    return instance.__class__.objects.filter(
        characterrelationshipmembership__character=instance,
        characterrelationshipmembership__relationship__relationship_type="romantic",
    )


def lifecycle_is_fertile(instance) -> bool:
    return instance.fertility > 0


def lifecycle_can_reproduce_with(instance, partner) -> bool:
    if instance.fertility <= 0 or partner.fertility <= 0:
        return False
    if (
        instance.sex == "Male"
        and partner.sex == "Male"
        or instance.sex == "Female"
        and partner.sex == "Female"
    ):
        return False
    return True


def lifecycle_attempt_pregnancy(instance) -> bool:
    romantic_partners = lifecycle_get_romantic_partners(instance)

    for partner in romantic_partners:
        if lifecycle_can_reproduce_with(instance, partner):
            if lifecycle_is_fertile(instance) and not instance.is_pregnant:
                lifecycle_start_pregnancy(instance, partner)
                return True
    return False


def lifecycle_start_pregnancy(instance, partner) -> None:
    instance.is_pregnant = True
    instance.pregnancy_start_date = timezone.now().date()
    instance.pregnancy_partner = partner

    instance.save()


def lifecycle_handle_childbirth(instance) -> None:
    from character.models import Character

    child_name = f"Child of {instance.first_name}"
    child = Character.objects.create(
        name=child_name,
        birth_date=timezone.now().date(),
        sex="Male" if randint(0, 1) == 0 else "Female",
    )

    child.parents.add(instance)
    if instance.pregnancy_partner:
        child.parents.add(instance.pregnancy_partner)
    child.save()


def lifecycle_handle_miscarriage(instance) -> None:
    instance.is_pregnant = False
    instance.pregnancy_start_date = None
    instance.save()


def lifecycle_get_miscarriage_change(instance) -> float:
    chance = 0.05
    if lifecycle_get_age(instance) > (40 * 365):
        chance += 0.10
    return round(chance, 5)
