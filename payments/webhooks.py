import logging

from django.conf import settings
from django.db import transaction

from payments.models import SubscriptionPlan, UserSubscription
from users.models import CustomUser

logger = logging.getLogger("general")


@transaction.atomic
def handle_subscription_event(subscription):
    """Update local subscription state from Stripe subscription webhook payload."""
    metadata = subscription.get("metadata", {}) or {}
    user_id = metadata.get("user_id")

    if not user_id:
        logger.warning(
            "[PAYMENTS.WEBHOOK] Missing user_id metadata on subscription %s",
            subscription.get("id"),
        )
        return

    try:
        user = CustomUser.objects.get(id=user_id)
    except CustomUser.DoesNotExist:
        logger.warning(
            "[PAYMENTS.WEBHOOK] User not found for webhook metadata user_id=%s", user_id
        )
        return

    user_subscription, _ = UserSubscription.objects.get_or_create(user=user)
    user_subscription.stripe_subscription_id = subscription.get("id")
    user_subscription.active = subscription.get("status") in {"active", "trialing"}

    price_id = (
        subscription.get("items", {}).get("data", [{}])[0].get("price", {}).get("id")
    )
    if price_id:
        user_subscription.plan = SubscriptionPlan.objects.filter(
            stripe_plan_id=price_id
        ).first()

    user_subscription.save(update_fields=["stripe_subscription_id", "active", "plan"])

    player = getattr(user, "player", None)
    if player:
        premium_price_ids = {
            getattr(settings, "STRIPE_PRICE_ID_PREMIUM_MONTHLY", ""),
            getattr(settings, "STRIPE_PRICE_ID_PREMIUM_ANNUAL", ""),
        }
        premium_price_ids.discard("")
        player.is_premium = user_subscription.active and bool(
            price_id and price_id in premium_price_ids
        )
        player.save(update_fields=["is_premium"])

    logger.info(
        "[PAYMENTS.WEBHOOK] Updated subscription %s for user %s",
        subscription.get("id"),
        user.id,
    )
