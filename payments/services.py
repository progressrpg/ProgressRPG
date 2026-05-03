import stripe
from django.conf import settings
from django.db import transaction

from payments.models import UserSubscription

stripe.api_key = settings.STRIPE_SECRET_KEY


@transaction.atomic
def end_active_subscription(user):
    """Cancel a user's active premium Stripe subscription and deactivate it locally."""
    active_sub = UserSubscription.active_for_user(user)
    if active_sub is None:
        return None

    if (
        active_sub.stripe_subscription_id
        and active_sub.plan
        and active_sub.plan.is_premium
    ):
        stripe.Subscription.cancel(active_sub.stripe_subscription_id)

    active_sub.deactivate()
    return active_sub
