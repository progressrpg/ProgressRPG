# character.signals
from datetime import timedelta, datetime, time
from django.db.models.signals import post_save, pre_delete, post_delete
from django.dispatch import receiver
from django.utils import timezone

import logging

from .models import (
    Character,
    CharacterRelationship,
    CharacterRelationshipMembership,
    PlayerCharacterLink,
    Behaviour,
    CharacterNeeds,
)

from progression.models import CharacterActivity

logger = logging.getLogger("general")


@receiver(post_save, sender=Character)
def create_behaviour(sender, instance, created, **kwargs):
    """Ensure every new Character has a behaviour instance."""
    if created:
        Behaviour.objects.get_or_create(character=instance)


@receiver(post_save, sender=Character)
def create_needs(sender, instance, created, **kwargs):
    """Ensure every new Character has a needs instance."""
    if created:
        CharacterNeeds.objects.get_or_create(character=instance)


@receiver(pre_delete, sender=PlayerCharacterLink)
def unlink_before_deletion(sender, instance, **kwargs):
    """Ensure the link is properly unlinked before deletion."""
    instance.unlink()


@receiver(post_delete, sender=CharacterRelationshipMembership)
def delete_relationship_with_no_members(sender, instance, **kwargs):
    """
    CharacterRelationshipMembership.character cascades on Character delete
    (e.g. generate_characters wiping unlinked Characters before
    regenerating a village's cast), but CharacterRelationship - the other
    side of the through table - has no FK of its own for Django to cascade
    from. Without this, a relationship whose members were all deleted
    survives forever as an orphaned, memberless row.
    """
    relationship_id = instance.relationship_id
    still_has_members = CharacterRelationshipMembership.objects.filter(
        relationship_id=relationship_id
    ).exists()
    if not still_has_members:
        CharacterRelationship.objects.filter(id=relationship_id).delete()
