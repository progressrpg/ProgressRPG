import stripe
from django.conf import settings
from django.db import transaction

from payments.models import UserSubscription

stripe.api_key = settings.STRIPE_SECRET_KEY


@transaction.atomic
def provision_free_subscription(user):
    """Create a Stripe subscription on the configured free price and persist it locally."""
    free_price_id = getattr(settings, "STRIPE_PRICE_ID_FREE", "")
    if not free_price_id:
        raise ValueError("Missing STRIPE_PRICE_ID_FREE setting")

    customer = stripe.Customer.create(
        email=user.email,
        metadata={"user_id": str(user.id)},
    )

    subscription = stripe.Subscription.create(
        customer=customer.id,
        items=[{"price": free_price_id}],
        metadata={"user_id": str(user.id)},
    )

    user_subscription, _ = UserSubscription.objects.get_or_create(user=user)
    user_subscription.stripe_subscription_id = subscription.id
    user_subscription.active = subscription.status in {"active", "trialing"}
    user_subscription.save(update_fields=["stripe_subscription_id", "active"])

    player = getattr(user, "player", None)
    if player:
        player.is_premium = False
        player.save(update_fields=["is_premium"])

    return user_subscription
