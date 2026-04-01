from payments.models import UserSubscription
from users.models import CustomUser


import logging

logger = logging.getLogger("django")


def extract_price_id(subscription):
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


def get_user_from_customer_id(customer_id):
    return CustomUser.objects.filter(stripe_customer_id=customer_id).first()


def resolve_user_from_checkout_session(session_object):
    customer_id = session_object.get("customer")
    user = get_user_from_customer_id(customer_id)
    if user:
        return user

    user_id = session_object.get("client_reference_id")
    if user_id:
        return CustomUser.objects.filter(id=user_id).first()

    return None


def resolve_subscription_payload_and_model(event, event_name):
    stripe_object = event["data"]["object"]

    if event_name == "subscription.updated":
        subscription_payload = stripe_object
    elif event_name in {"subscription.deleted", "invoice.payment_failed"}:
        subscription_payload = (
            stripe_object.get("subscription")
            if event_name == "invoice.payment_failed"
            else stripe_object
        )
    else:
        subscription_payload = stripe_object

    if isinstance(subscription_payload, str):
        logger.warning(
            f"[PAYMENTS.WEBHOOK] {event_name} received subscription id string only "
            f"(subscription_id={subscription_payload})"
        )
        return None, subscription_payload, None, None

    if not isinstance(subscription_payload, dict):
        logger.warning(f"[PAYMENTS.WEBHOOK] {event_name} missing subscription payload")
        return None, None, None, None

    subscription_id = subscription_payload.get("id")
    customer_id = subscription_payload.get("customer")

    user = get_user_from_customer_id(customer_id)
    if not user:
        logger.warning(
            f"[PAYMENTS.WEBHOOK] {event_name} for unknown "
            f"customer_id={customer_id} subscription_id={subscription_id}"
        )
        return None, subscription_id, subscription_payload, None

    subscription = (
        UserSubscription.objects.filter(
            user=user,
            stripe_subscription_id=subscription_id,
        )
        .select_related("plan")
        .first()
    )

    if not subscription:
        logger.warning(
            f"[PAYMENTS.WEBHOOK] {event_name} for unknown subscription "
            f"(subscription_id={subscription_id}, customer_id={customer_id})"
        )

    return user, subscription_id, subscription_payload, subscription


def resolve_subscription_from_event(event, event_name):
    stripe_object = event["data"]["object"]

    subscription_id = stripe_object.get("id")
    customer_id = stripe_object.get("customer")

    user = get_user_from_customer_id(customer_id)

    subscription = (
        UserSubscription.objects.filter(
            user=user,
            stripe_subscription_id=subscription_id,
        )
        .select_related("plan")
        .first()
    )

    if not subscription:
        logger.warning(
            f"[PAYMENTS.WEBHOOK] {event_name} for unknown (subscription_id={subscription_id}, customer_id={customer_id})"
        )
        return None, subscription_id, None

    return user, subscription_id, subscription
