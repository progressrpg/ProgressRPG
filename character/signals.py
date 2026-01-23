# character.signals
from datetime import timedelta, datetime, time
from django.db import transaction
from django.db.models.signals import pre_save, post_save, pre_delete, post_delete
from django.dispatch import receiver
from django.utils import timezone

import logging

from .models import Character, PlayerCharacterLink, Behaviour

from gameplay.models import QuestTimer
from progression.models import CharacterActivity

logger = logging.getLogger("general")


@receiver(post_save, sender=Character)
def create_timer(sender, instance, created, **kwargs):
    """Create a quest timer for a new character"""
    if created:
        quest_timer = QuestTimer.objects.create(character=instance)


@receiver(post_save, sender=Character)
def create_behaviour(sender, instance, created, **kwargs):
    """Ensure every Character has a behaviour instance."""
    Behaviour.objects.get_or_create(character=instance)


@receiver(pre_delete, sender=PlayerCharacterLink)
def unlink_before_deletion(sender, instance, **kwargs):
    """Ensure the link is properly unlinked before deletion."""
    instance.unlink()


def recompute_character_flags(character_id: int) -> None:
    """
    Recompute denormalised flags for a Character based on current links.
    Adjust the logic here to match your rules.
    A character can_link if they have no active player links.
    """
    if not character_id:
        return

    # Character can link if they don't have any active player links
    has_active_link = PlayerCharacterLink.objects.filter(
        character_id=character_id, is_active=True
    ).exists()

    can_link = not has_active_link

    Character.objects.filter(id=character_id).update(
        can_link=can_link,
    )
    


@receiver(pre_save, sender=PlayerCharacterLink)
def link_presave_track_old_character(sender, instance, **kwargs):
    """
    If someone edits a link and changes its character, we need to update BOTH:
    the old character and the new character.
    """
    instance._old_character_id = None
    if instance.pk:
        try:
            old = PlayerCharacterLink.objects.only("character_id").get(pk=instance.pk)
            instance._old_character_id = old.character_id
        except PlayerCharacterLink.DoesNotExist:
            pass


@receiver(post_save, sender=PlayerCharacterLink)
def link_postsave_recompute(sender, instance, **kwargs):
    def _do():
        # update new/current character
        recompute_character_flags(instance.character_id)
        # update old character if link moved
        old_id = getattr(instance, "_old_character_id", None)
        if old_id and old_id != instance.character_id:
            recompute_character_flags(old_id)

    transaction.on_commit(_do)


@receiver(post_delete, sender=PlayerCharacterLink)
def link_postdelete_recompute(sender, instance, **kwargs):
    transaction.on_commit(lambda: recompute_character_flags(instance.character_id))
