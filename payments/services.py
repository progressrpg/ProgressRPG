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

    free_plan = SubscriptionPlan.objects.filter(stripe_price_id=free_price_id).first()
    if not free_plan:
        raise ValueError(
            f"No SubscriptionPlan configured for STRIPE_PRICE_ID_FREE={free_price_id}"
        )

    customer_id = user.stripe_customer_id
    if not customer_id:
        customer = stripe.Customer.create(
            email=user.email,
            metadata={"user_id": str(user.id)},
        )
        customer_id = customer.id
        user.stripe_customer_id = customer_id
        user.save(update_fields=["stripe_customer_id"])

    subscription = stripe.Subscription.create(
        customer=customer_id,
        items=[{"price": free_price_id}],
        metadata={"user_id": str(user.id)},
        idempotency_key=f"free-subscription:{user.id}:{free_price_id}",
    )

    subscription_id = subscription.id
    user_subscription, _ = UserSubscription.objects.get_or_create(
        stripe_subscription_id=subscription_id,
        defaults={"user": user},
    )

    user_subscription.user = user
    user_subscription.active = subscription.status in {"active", "trialing"}
    user_subscription.plan = free_plan
    user_subscription.save(update_fields=["user", "active", "plan"])

    if user_subscription.active:
        UserSubscription.deactivate_all_for_user(user)
        user_subscription.activate()

    return user_subscription
