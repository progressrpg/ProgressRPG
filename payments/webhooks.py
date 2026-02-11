import stripe
from django.conf import settings
from users.models import CustomUser
from django.utils import timezone
import logging

stripe.api_key = settings.STRIPE_SECRET_KEY

logger = logging.getLogger("general")


def handle_subscription_event(subscription):
    customer_id = subscription["customer"]

    try:
        user = CustomUser.objects.get(stripe_customer_id=customer_id)
    except CustomUser.DoesNotExist:
        return

    logger.info(f"Stripe webhook event {subscription['id']} for user {user.id} handled")

    user.subscription_status = subscription["status"]
    user.current_price_id = subscription["items"]["data"][0]["price"]["id"]

    # Optional but recommended
    if subscription.get("current_period_end"):
        user.subscription_current_period_end = timezone.datetime.fromtimestamp(
            subscription["current_period_end"],
            tz=timezone.utc,
        )

    user.save()
