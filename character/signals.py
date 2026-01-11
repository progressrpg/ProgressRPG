# character.signals

from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from .models import Character, PlayerCharacterLink, Behaviour

from gameplay.models import QuestTimer


@receiver(post_save, sender=Character)
def create_timer(sender, instance, created, **kwargs):
    """Create a quest timer for a new character"""
    if created:
        quest_timer = QuestTimer.objects.create(character=instance)


@receiver(post_save, sender=Character)
def create_behaviour(sender, instance, created, **kwargs):
    """Create a behaviour instance for a new character"""
    if created:
        behaviour = Behaviour.objects.create(character=instance)


@receiver(pre_delete, sender=PlayerCharacterLink)
def unlink_before_deletion(sender, instance, **kwargs):
    character = instance.character
    character.is_npc = True
    character.save(update_fields=["is_npc"])

    instance.unlink()
