from django.db import IntegrityError
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Quest, QuestResults, ServerMessage, ActivityTimer
from .utils import send_group_message
from users.models import Player

import logging

logger = logging.getLogger("general")


@receiver(post_save, sender=Player)
def create_activity_timer(sender, instance, created, **kwargs):
    """Create an activity timer for the player when a new player is created"""
    if created:
        ActivityTimer.objects.create(player=instance)
        logger.info(
            f"[CREATE ACTIVITY TIMER] New activity timer created for player {instance.id}"
        )


@receiver(post_save, sender=Quest)
def create_quest_results(sender, instance, created, **kwargs):
    """Creates QuestResults for new quests."""
    if created:
        try:
            QuestResults.objects.create(quest=instance)
            logger.info(
                f"[CREATE QUEST RESULTS] Quest results created for quest: {instance.id}"
            )
        except IntegrityError as e:
            logger.error(
                f"[CREATE QUEST RESULTS] IntegrityError while creating quest results for quest {instance.id}: {e}",
                exc_info=True,
            )
        except Exception as e:
            logger.error(
                f"[CREATE QUEST RESULTS] Unexpected error while creating quest results for quest {instance.id}: {e}",
                exc_info=True,
            )


@receiver(post_save, sender=ServerMessage)
def server_message_created(sender, instance, created, **kwargs):
    """Triggers consumer to run message send method when a new server message is created."""
    if created and not instance.is_draft:
        from asgiref.sync import async_to_sync
        from channels.layers import get_channel_layer

        channel_layer = get_channel_layer()
        async_to_sync(send_group_message)(
            instance.group, {"type": "send_pending_messages"}
        )
