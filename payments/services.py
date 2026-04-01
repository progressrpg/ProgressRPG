import stripe
from django.conf import settings
from django.db import transaction

from payments.models import SubscriptionPlan, UserSubscription

stripe.api_key = settings.STRIPE_SECRET_KEY


@transaction.atomic
def provision_free_subscription(user):
    """Create a Stripe subscription on the configured free price and persist it locally."""
    current_subscription = UserSubscription.current_for_user(user)
    if current_subscription and current_subscription.active:
        return current_subscription

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

    subscription_id = subscription.id
    user_subscription, _ = UserSubscription.objects.get_or_create(
        stripe_subscription_id=subscription_id,
        defaults={"user": user},
    )

    user_subscription.user = user
    user_subscription.active = subscription.status in {"active", "trialing"}
    user_subscription.plan = SubscriptionPlan.objects.filter(
        stripe_price_id=free_price_id
    ).first()
    user_subscription.save(update_fields=["user", "active", "plan"])

    if user_subscription.active:
        UserSubscription.objects.filter(user=user, active=True).exclude(
            pk=user_subscription.pk
        ).update(active=False)

    return user_subscription
