import logging
import stripe
from datetime import datetime, timezone as dt_timezone

from django.conf import settings
from django.db import transaction

from payments.models import SubscriptionPlan, UserSubscription
from users.models import CustomUser

logger = logging.getLogger("general")
stripe.api_key = settings.STRIPE_SECRET_KEY


def _to_datetime(value):
    if not value:
        return None
    return datetime.fromtimestamp(value, tz=dt_timezone.utc)


def _extract_price_id(subscription):
    item = subscription.get("items", {}).get("data", [{}])[0]

    # Stripe may send `price` as an object or string depending on expand/config.
    price = item.get("price")
    if isinstance(price, dict):
        price_id = price.get("id")
    elif isinstance(price, str):
        price_id = price
    else:
        price_id = None

    # Backward-compatible fallback for older payload shapes.
    if not price_id:
        plan = item.get("plan")
        if isinstance(plan, dict):
            price_id = plan.get("id")
        elif isinstance(plan, str):
            price_id = plan

    return price_id


@transaction.atomic
def handle_subscription_event(subscription, user_id_hint=None):
    """Update local subscription state from Stripe subscription webhook payload."""
    metadata = subscription.get("metadata", {}) or {}
    user_id = metadata.get("user_id") or user_id_hint
    subscription_id = subscription.get("id")

    logger.info(
        "[PAYMENTS.WEBHOOK] Processing subscription event subscription_id=%s status=%s metadata_user_id=%s user_id_hint=%s",
        subscription_id,
        subscription.get("status"),
        metadata.get("user_id"),
        user_id_hint,
    )

    if not user_id:
        existing = (
            UserSubscription.objects.select_related("user")
            .filter(stripe_subscription_id=subscription_id)
            .first()
        )
        if existing:
            user = existing.user
            logger.info(
                "[PAYMENTS.WEBHOOK] Resolved user_id=%s from existing local subscription_id=%s",
                user.id,
                subscription_id,
            )
        else:
            logger.warning(
                "[PAYMENTS.WEBHOOK] Missing user_id metadata on subscription %s",
                subscription_id,
            )
            return
    else:
        try:
            user = CustomUser.objects.get(id=user_id)
        except CustomUser.DoesNotExist:
            logger.warning(
                "[PAYMENTS.WEBHOOK] User not found for webhook metadata user_id=%s",
                user_id,
            )
            return

    if subscription_id:
        user_subscription, created = UserSubscription.objects.get_or_create(
            stripe_subscription_id=subscription_id,
            defaults={"user": user},
        )
        logger.info(
            "[PAYMENTS.WEBHOOK] %s local subscription record for subscription_id=%s user_id=%s",
            "Created" if created else "Found",
            subscription_id,
            user.id,
        )
    else:
        user_subscription = UserSubscription(user=user)
        logger.warning(
            "[PAYMENTS.WEBHOOK] Subscription payload missing id for user_id=%s",
            user.id,
        )

    user_subscription.user = user
    user_subscription.stripe_subscription_id = subscription_id
    user_subscription.active = subscription.get("status") in {"active", "trialing"}
    user_subscription.start_date = (
        _to_datetime(subscription.get("start_date")) or user_subscription.start_date
    )

    # Use current period end where available; otherwise fall back to explicit end signals.
    user_subscription.end_date = (
        _to_datetime(subscription.get("current_period_end"))
        or _to_datetime(subscription.get("ended_at"))
        or _to_datetime(subscription.get("cancel_at"))
    )

    price_id = _extract_price_id(subscription)
    logger.info(
        "[PAYMENTS.WEBHOOK] Extracted price_id=%s for subscription_id=%s",
        price_id,
        subscription_id,
    )
    if price_id:
        user_subscription.plan = SubscriptionPlan.objects.filter(
            stripe_plan_id=price_id
        ).first()
        if user_subscription.plan:
            logger.info(
                "[PAYMENTS.WEBHOOK] Matched plan_id=%s plan_name=%s is_premium=%s for price_id=%s",
                user_subscription.plan.id,
                user_subscription.plan.name,
                user_subscription.plan.is_premium,
                price_id,
            )
        else:
            logger.warning(
                "[PAYMENTS.WEBHOOK] No SubscriptionPlan found for price_id=%s; user_id=%s will remain non-premium",
                price_id,
                user.id,
            )
    else:
        logger.warning(
            "[PAYMENTS.WEBHOOK] Unable to extract price_id from subscription payload for subscription_id=%s",
            subscription_id,
        )

    if user_subscription.pk:
        user_subscription.save(
            update_fields=[
                "user",
                "stripe_subscription_id",
                "active",
                "plan",
                "start_date",
                "end_date",
            ]
        )
    else:
        user_subscription.save()

    if user_subscription.active:
        demoted_count = (
            UserSubscription.objects.filter(user=user, active=True)
            .exclude(pk=user_subscription.pk)
            .update(active=False)
        )
        if demoted_count:
            logger.info(
                "[PAYMENTS.WEBHOOK] Deactivated %s other active subscriptions for user_id=%s",
                demoted_count,
                user.id,
            )

    logger.info(
        "[PAYMENTS.WEBHOOK] Updated subscription_id=%s user_id=%s active=%s plan_id=%s computed_is_active_premium=%s",
        subscription_id,
        user.id,
        user_subscription.active,
        user_subscription.plan_id,
        user_subscription.is_active_premium,
    )


def handle_checkout_session_completed(session):
    """Sync subscription state after checkout completion as a fallback path."""
    subscription_id = session.get("subscription")
    if not subscription_id:
        logger.warning(
            "[PAYMENTS.WEBHOOK] checkout.session.completed missing subscription id session_id=%s",
            session.get("id"),
        )
        return

    user_id_hint = session.get("client_reference_id")
    logger.info(
        "[PAYMENTS.WEBHOOK] Handling checkout.session.completed session_id=%s subscription_id=%s client_reference_id=%s",
        session.get("id"),
        subscription_id,
        user_id_hint,
    )
    subscription = stripe.Subscription.retrieve(subscription_id)
    handle_subscription_event(subscription, user_id_hint=user_id_hint)
