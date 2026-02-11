# payments/services.py

import stripe
from django.conf import settings
from django.db import transaction
from users.models import CustomUser
from django.utils import timezone

stripe.api_key = settings.STRIPE_SECRET_KEY


def provision_free_subscription(user: CustomUser):
    if user.stripe_customer_id:
        return

    # 1. Create Stripe Customer
    customer = stripe.Customer.create(
        email=user.email,
        metadata={
            "user_id": user.id,
        },
    )

    # 2. Create Free Subscription
    subscription = stripe.Subscription.create(
        customer=customer.id,
        items=[
            {
                "price": settings.STRIPE_FREE_PRICE_ID,
            }
        ],
    )

    # 3. Store on user
    with transaction.atomic():
        user.stripe_customer_id = customer.id
        user.stripe_subscription_id = subscription.id
        user.subscription_status = subscription.status
        user.current_price_id = settings.STRIPE_FREE_PRICE_ID
        user.subscription_current_period_end = subscription.current_period_end
        user.save()
