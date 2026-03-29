import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

from payments.services import provision_free_subscription

logger = logging.getLogger("general")

User = get_user_model()


@receiver(post_save, sender=User)
def provision_default_subscription(sender, instance, created, raw=False, **kwargs):
    if raw or not created:
        return

    free_price_id = getattr(settings, "STRIPE_PRICE_ID_FREE", "")
    stripe_secret_key = getattr(settings, "STRIPE_SECRET_KEY", "")
    if not free_price_id or not stripe_secret_key:
        return

    try:
        provision_free_subscription(instance)
    except Exception:
        logger.exception(
            "[PAYMENTS.SIGNALS] Failed to provision free subscription for user %s",
            instance.id,
        )
