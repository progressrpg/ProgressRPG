from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import ServerMessage
from .utils import send_group_message

import logging

logger = logging.getLogger("general")


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
