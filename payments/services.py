import logging
from datetime import datetime, timezone as dt_timezone

import stripe
from django.conf import settings
from django.db import transaction
from django.db.models import Q

from payments.models import SubscriptionPlan, UserSubscription
from payments.utils import extract_price_id

logger = logging.getLogger("general")
stripe.api_key = settings.STRIPE_SECRET_KEY

ACTIVE_STATUSES = {"active", "trialing"}
DEAD_STATUSES = {"canceled", "incomplete_expired", "unpaid"}


@transaction.atomic
def end_active_subscription(user):
    """Cancel a user's active Stripe subscription and deactivate it locally."""
    active_sub = UserSubscription.active_for_user(user)
    if active_sub is None:
        logger.info(
            "[PAYMENTS.SERVICES] No active subscription to cancel for user_id=%s",
            user.id,
        )
        return None

    if active_sub.stripe_subscription_id:
        try:
            stripe.Subscription.cancel(active_sub.stripe_subscription_id)
            logger.info(
                "[PAYMENTS.SERVICES] Cancelled Stripe subscription %s for user_id=%s",
                active_sub.stripe_subscription_id,
                user.id,
            )
        except stripe.error.InvalidRequestError as exc:
            # Subscription no longer exists in Stripe (e.g. deleted manually,
            # or created in a different environment). Deactivate locally anyway.
            logger.warning(
                "[PAYMENTS.SERVICES] Stripe subscription %s not found for user_id=%s, deactivating locally only: %s",
                active_sub.stripe_subscription_id,
                user.id,
                exc,
            )

    active_sub.deactivate()
    logger.info(
        "[PAYMENTS.SERVICES] Deactivated subscription id=%s for user_id=%s",
        active_sub.id,
        user.id,
    )
    return active_sub


def _fetch_stripe_subscriptions(user):
    """
    Fetch subscriptions from Stripe for a user. Returns a list of Stripe subscription
    objects and also fixes stripe_customer_id on the user if it was missing or stale.

    Resolution order:
    1. List by stored customer ID
    2. If customer ID missing or stale, retrieve by local subscription ID and fix customer ID
    """
    customer_id = getattr(user, "stripe_customer_id", None)

    if customer_id:
        try:
            result = stripe.Subscription.list(
                customer=customer_id,
                status="all",
                limit=10,
                expand=["data.items.data.price"],
            )
            return list(getattr(result, "data", []))
        except stripe.error.InvalidRequestError as exc:
            if exc.code != "resource_missing" or exc.param != "customer":
                raise
            logger.warning(
                "[PAYMENTS.SYNC] Stored customer_id=%s not found in Stripe for user_id=%s "
                "— falling back to local subscription lookup",
                customer_id,
                user.id,
            )
            # Fall through to subscription-ID lookup below

    # No customer ID, or stale one — try local subscription ID first
    local_sub = UserSubscription.active_for_user(user)
    if local_sub and local_sub.stripe_subscription_id:
        logger.info(
            "[PAYMENTS.SYNC] Retrieving subscription for user_id=%s via subscription_id=%s",
            user.id,
            local_sub.stripe_subscription_id,
        )
        try:
            stripe_sub = stripe.Subscription.retrieve(
                local_sub.stripe_subscription_id,
                expand=["items.data.price"],
            )
            real_customer_id = getattr(stripe_sub, "customer", None)
            if real_customer_id and real_customer_id != customer_id:
                user.stripe_customer_id = real_customer_id
                user.save(update_fields=["stripe_customer_id"])
            return [stripe_sub]
        except stripe.error.InvalidRequestError as exc:
            if exc.code != "resource_missing":
                raise
            logger.warning(
                "[PAYMENTS.SYNC] Local subscription_id=%s not found in Stripe for user_id=%s "
                "— falling back to email lookup",
                local_sub.stripe_subscription_id,
                user.id,
            )

    # Last resort: search Stripe for a customer by email
    email = getattr(user, "email", None)
    if not email:
        logger.info(
            "[PAYMENTS.SYNC] No stripe_customer_id, no local subscription, and no email "
            "for user_id=%s — nothing to sync",
            user.id,
        )
        return []

    logger.info(
        "[PAYMENTS.SYNC] Searching Stripe for customer by email=%s for user_id=%s",
        email,
        user.id,
    )
    customers = stripe.Customer.search(query=f'email:"{email}"', limit=5)
    customer_data = list(getattr(customers, "data", []))
    if not customer_data:
        logger.info(
            "[PAYMENTS.SYNC] No Stripe customer found for email=%s user_id=%s",
            email,
            user.id,
        )
        return []

    # Use the most recently created customer
    stripe_customer = sorted(customer_data, key=lambda c: c.created, reverse=True)[0]
    real_customer_id = stripe_customer.id
    logger.info(
        "[PAYMENTS.SYNC] Found Stripe customer_id=%s for email=%s user_id=%s",
        real_customer_id,
        email,
        user.id,
    )
    user.stripe_customer_id = real_customer_id
    user.save(update_fields=["stripe_customer_id"])

    result = stripe.Subscription.list(
        customer=real_customer_id,
        status="all",
        limit=10,
        expand=["data.items.data.price"],
    )
    return list(getattr(result, "data", []))


def _backfill_historical_subscriptions(user, subscriptions_data):
    """
    Ensure every Stripe subscription Stripe knows about (active or not) has a
    matching local UserSubscription row, so trial-history checks
    (has_previous_subscription) don't depend entirely on webhook delivery.
    Rows are always created inactive; the active/dead branches below then
    activate the candidate's row if its Stripe status warrants it.
    """
    for stripe_sub in subscriptions_data:
        if UserSubscription.objects.filter(
            stripe_subscription_id=stripe_sub.id
        ).exists():
            continue

        price_id = extract_price_id(stripe_sub)
        plan = (
            SubscriptionPlan.objects.filter(stripe_price_id=price_id).first()
            if price_id
            else None
        )
        ended_at = getattr(stripe_sub, "ended_at", None) or getattr(
            stripe_sub, "canceled_at", None
        )
        local_sub = UserSubscription.objects.create(
            user=user,
            plan=plan,
            stripe_subscription_id=stripe_sub.id,
            active=False,
        )
        if ended_at:
            local_sub.end_date = datetime.fromtimestamp(ended_at, tz=dt_timezone.utc)
            local_sub.save(update_fields=["end_date"])
        logger.info(
            "[PAYMENTS.SYNC] Backfilled missing local subscription id=%s for "
            "user_id=%s stripe_subscription_id=%s status=%s",
            local_sub.id,
            user.id,
            stripe_sub.id,
            stripe_sub.status,
        )


def _reconcile_subscriptions(user, subscriptions_data):
    """Apply a list of Stripe subscription objects to local state."""
    live = [s for s in subscriptions_data if s.status in ACTIVE_STATUSES]
    candidate = (
        live[0] if live else (subscriptions_data[0] if subscriptions_data else None)
    )
    logger.debug(
        "[PAYMENTS.SYNC] Reconciling %d Stripe subscriptions for user_id=%s, "
        "candidate subscription_id=%s status=%s",
        len(subscriptions_data),
        user.id,
        getattr(candidate, "id", None),
        getattr(candidate, "status", None),
    )
    _backfill_historical_subscriptions(user, subscriptions_data)

    if not candidate:
        UserSubscription.deactivate_all_for_user(user)
        logger.info(
            "[PAYMENTS.SYNC] No Stripe subscriptions for user_id=%s — deactivated all local",
            user.id,
        )
        return {"status": "none", "synced": True}

    stripe_sub_id = candidate.id
    stripe_status = candidate.status
    price_id = extract_price_id(candidate)
    plan = (
        SubscriptionPlan.objects.filter(stripe_price_id=price_id).first()
        if price_id
        else None
    )

    if stripe_status in ACTIVE_STATUSES:
        local_sub = UserSubscription.objects.filter(
            stripe_subscription_id=stripe_sub_id
        ).first()
        if not local_sub:
            UserSubscription.deactivate_all_for_user(user)
            local_sub = UserSubscription.objects.create(
                user=user,
                plan=plan,
                stripe_subscription_id=stripe_sub_id,
                active=True,
            )
            logger.info(
                "[PAYMENTS.SYNC] Created missing local subscription id=%s for user_id=%s "
                "stripe_subscription_id=%s status=%s",
                local_sub.id,
                user.id,
                stripe_sub_id,
                stripe_status,
            )
        else:
            if plan and local_sub.plan != plan:
                local_sub.plan = plan
                local_sub.save(update_fields=["plan"])
            if not local_sub.active:
                local_sub.activate()
                logger.info(
                    "[PAYMENTS.SYNC] Reactivated local subscription id=%s for user_id=%s",
                    local_sub.id,
                    user.id,
                )
        return {"status": stripe_status, "synced": True}

    if stripe_status in DEAD_STATUSES:
        local_sub = UserSubscription.objects.filter(
            stripe_subscription_id=stripe_sub_id, active=True
        ).first()
        logger.debug(
            "[PAYMENTS.SYNC] Stripe subscription status is '%s' for user_id=%s, "
            "looking for active local subscription with stripe_subscription_id=%s: "
            "found local_sub id=%s",
            stripe_status,
            user.id,
            stripe_sub_id,
            getattr(local_sub, "id", None),
        )
        if local_sub:
            local_sub.deactivate()
            logger.info(
                "[PAYMENTS.SYNC] Deactivated local subscription id=%s for user_id=%s "
                "stripe_status=%s",
                local_sub.id,
                user.id,
                stripe_status,
            )
        return {"status": stripe_status, "synced": True}

    return {"status": stripe_status, "synced": False}


@transaction.atomic
def sync_subscription_from_stripe(user):
    """
    Fetch the user's current subscription(s) from Stripe and reconcile local state.
    Returns a dict: {"status": "active"|"trialing"|"none", "synced": bool}.
    """
    subscriptions_data = _fetch_stripe_subscriptions(user)
    logger.info(
        "[PAYMENTS.SERVICES] Fetched %d Stripe subscriptions for user_id=%s",
        len(subscriptions_data),
        user.id,
    )
    return _reconcile_subscriptions(user, subscriptions_data)


# ---------------------------------------------------------------------------
# Full account sync (use after switching between Stripe sandbox / live keys)
# ---------------------------------------------------------------------------


def _sync_plans(dry_run=False):
    """
    Pull all active Stripe prices and reconcile local SubscriptionPlan records.
    Plans are matched by (name, interval); missing plans are created from Stripe data.
    Returns {"created": int, "updated": int, "skipped": int}.
    """
    from decimal import Decimal

    interval_map = {"month": "monthly", "year": "annual"}
    result = {"created": 0, "updated": 0, "skipped": 0, "removed": 0, "changes": []}
    seen_price_ids = set()

    prices = stripe.Price.list(active=True, expand=["data.product"], limit=100)
    for price in prices.auto_paging_iter():
        seen_price_ids.add(price.id)
        product = getattr(price, "product", None)
        if not product or isinstance(product, str):
            continue
        if not getattr(product, "active", True):
            continue
        product_name = getattr(product, "name", "").strip()
        recurring = getattr(price, "recurring", None)
        if not recurring:
            continue
        raw_interval = getattr(recurring, "interval", "")
        interval = interval_map.get(raw_interval)
        if not interval:
            continue

        unit_amount = getattr(price, "unit_amount", None)
        new_price_dollars = (
            Decimal(str(round(unit_amount / 100, 2))) if unit_amount else Decimal("0")
        )

        plan = SubscriptionPlan.objects.filter(stripe_price_id=price.id).first()
        if plan is None:
            plan = (
                SubscriptionPlan.objects.filter(
                    name__iexact=product_name,
                    interval=interval,
                )
                .filter(Q(stripe_price_id__isnull=True) | Q(stripe_price_id=""))
                .first()
            )

        if plan is None:
            logger.info(
                "[PAYMENTS.FULLSYNC] %sCreating SubscriptionPlan %r interval=%s price_id=%s",
                "[DRY RUN] " if dry_run else "",
                product_name,
                interval,
                price.id,
            )
            if not dry_run:
                SubscriptionPlan.objects.create(
                    name=product_name,
                    interval=interval,
                    stripe_price_id=price.id,
                    price=new_price_dollars,
                )
            result["created"] += 1
            result["changes"].append(
                f"  [create] plan {product_name!r} ({interval}) price_id={price.id} price={new_price_dollars}"
            )
            continue

        fields_changed = []
        if plan.stripe_price_id != price.id:
            fields_changed.append(
                f"stripe_price_id: {plan.stripe_price_id!r} → {price.id!r}"
            )
            if not dry_run:
                plan.stripe_price_id = price.id
        if unit_amount is not None and plan.price != new_price_dollars:
            fields_changed.append(f"price: {plan.price} → {new_price_dollars}")
            if not dry_run:
                plan.price = new_price_dollars

        if fields_changed:
            if not dry_run:
                update_fields = [
                    f
                    for f in ("stripe_price_id", "price")
                    if any(f in change for change in fields_changed)
                ]
                plan.save(update_fields=update_fields)
            logger.info(
                "[PAYMENTS.FULLSYNC] %sUpdated plan %r: %s",
                "[DRY RUN] " if dry_run else "",
                plan.name,
                ", ".join(fields_changed),
            )
            result["updated"] += 1
            result["changes"].append(
                f"  [update] plan {plan.name!r}: {', '.join(fields_changed)}"
            )
        else:
            result["skipped"] += 1

    # Remove stale plans whose price_id is no longer active in Stripe
    stale = SubscriptionPlan.objects.exclude(
        Q(stripe_price_id__isnull=True) | Q(stripe_price_id="")
    ).exclude(stripe_price_id__in=seen_price_ids)
    for plan in stale:
        has_subs = plan.usersubscription_set.exists()
        if has_subs:
            logger.warning(
                "[PAYMENTS.FULLSYNC] %sStale plan %r (price_id=%s) has subscriptions — "
                "clearing stripe_price_id only",
                "[DRY RUN] " if dry_run else "",
                plan.name,
                plan.stripe_price_id,
            )
            if not dry_run:
                plan.stripe_price_id = None
                plan.save(update_fields=["stripe_price_id"])
            result["changes"].append(
                f"  [clear] plan {plan.name!r} price_id={plan.stripe_price_id} (has subscriptions)"
            )
        else:
            logger.info(
                "[PAYMENTS.FULLSYNC] %sDeleting stale plan %r (price_id=%s)",
                "[DRY RUN] " if dry_run else "",
                plan.name,
                plan.stripe_price_id,
            )
            if not dry_run:
                plan.delete()
            result["changes"].append(
                f"  [delete] plan {plan.name!r} price_id={plan.stripe_price_id}"
            )
        result["removed"] += 1

    return result


def _sync_customers(dry_run=False):
    """
    Pull all Stripe customers and update CustomUser.stripe_customer_id where it
    differs or is missing. Matched by email. Returns {"updated": int, "skipped": int}.
    """
    from users.models import CustomUser

    result = {"updated": 0, "skipped": 0, "changes": []}
    customers = stripe.Customer.list(limit=100)
    for customer in customers.auto_paging_iter():
        email = getattr(customer, "email", None)
        if not email:
            continue
        user = CustomUser.objects.filter(email=email).first()
        if user is None:
            logger.debug(
                "[PAYMENTS.FULLSYNC] No local user for Stripe customer %s (email=%s)",
                customer.id,
                email,
            )
            continue
        if user.stripe_customer_id == customer.id:
            result["skipped"] += 1
            continue
        logger.info(
            "[PAYMENTS.FULLSYNC] %sUpdating stripe_customer_id for user_id=%s: %r → %r",
            "[DRY RUN] " if dry_run else "",
            user.id,
            user.stripe_customer_id,
            customer.id,
        )
        if not dry_run:
            user.stripe_customer_id = customer.id
            user.save(update_fields=["stripe_customer_id"])
        result["updated"] += 1
        result["changes"].append(
            f"  [update] customer {email}: {user.stripe_customer_id!r} → {customer.id!r}"
        )

    return result


def _sync_subscriptions(dry_run=False):
    """
    Pull all Stripe subscriptions (all statuses) and reconcile local UserSubscription
    records. Depends on stripe_price_id and stripe_customer_id being up to date, so
    run _sync_plans and _sync_customers first.
    Returns {"created": int, "updated": int, "deactivated": int, "skipped": int}.
    """
    from users.models import CustomUser

    result = {"created": 0, "updated": 0, "deactivated": 0, "skipped": 0, "changes": []}
    seen_stripe_ids = set()

    subscriptions = stripe.Subscription.list(
        status="all",
        limit=100,
        expand=["data.customer", "data.items.data.price"],
    )
    for stripe_sub in subscriptions.auto_paging_iter():
        seen_stripe_ids.add(stripe_sub.id)
        customer = getattr(stripe_sub, "customer", None)
        email = (
            getattr(customer, "email", None) if not isinstance(customer, str) else None
        )
        customer_id = customer.id if not isinstance(customer, str) else customer

        user = CustomUser.objects.filter(stripe_customer_id=customer_id).first()
        if user is None and email:
            user = CustomUser.objects.filter(email=email).first()
        if user is None:
            logger.debug(
                "[PAYMENTS.FULLSYNC] No local user for subscription %s (customer=%s)",
                stripe_sub.id,
                customer_id,
            )
            result["skipped"] += 1
            continue

        price_id = extract_price_id(stripe_sub)
        plan = (
            SubscriptionPlan.objects.filter(stripe_price_id=price_id).first()
            if price_id
            else None
        )

        status = stripe_sub.status
        local_sub = UserSubscription.objects.filter(
            stripe_subscription_id=stripe_sub.id
        ).first()

        if status in ACTIVE_STATUSES:
            if local_sub is None:
                if not dry_run:
                    UserSubscription.deactivate_all_for_user(user)
                    UserSubscription.objects.create(
                        user=user,
                        plan=plan,
                        stripe_subscription_id=stripe_sub.id,
                        active=True,
                    )
                logger.info(
                    "[PAYMENTS.FULLSYNC] %sCreated UserSubscription for user_id=%s stripe_sub=%s",
                    "[DRY RUN] " if dry_run else "",
                    user.id,
                    stripe_sub.id,
                )
                result["created"] += 1
                result["changes"].append(
                    f"  [create] subscription for {getattr(user, 'email', user.id)} stripe_sub={stripe_sub.id} status={status}"
                )
            else:
                changes = []
                if plan and local_sub.plan != plan:
                    changes.append(f"plan: {local_sub.plan} → {plan}")
                    if not dry_run:
                        local_sub.plan = plan
                if not local_sub.active:
                    changes.append("active: False → True")
                    if not dry_run:
                        local_sub.activate()
                    result["updated"] += 1
                if changes:
                    if not dry_run and "plan" in " ".join(changes):
                        local_sub.save(update_fields=["plan"])
                    logger.info(
                        "[PAYMENTS.FULLSYNC] %sUpdated subscription id=%s for user_id=%s: %s",
                        "[DRY RUN] " if dry_run else "",
                        local_sub.id,
                        user.id,
                        ", ".join(changes),
                    )
                    result["updated"] += 1
                    result["changes"].append(
                        f"  [update] subscription for {getattr(user, 'email', user.id)}: {', '.join(changes)}"
                    )
                else:
                    result["skipped"] += 1

        elif status in DEAD_STATUSES:
            if local_sub and local_sub.active:
                logger.info(
                    "[PAYMENTS.FULLSYNC] %sDeactivating subscription id=%s for user_id=%s (Stripe status=%s)",
                    "[DRY RUN] " if dry_run else "",
                    local_sub.id,
                    user.id,
                    status,
                )
                if not dry_run:
                    local_sub.deactivate()
                result["deactivated"] += 1
                result["changes"].append(
                    f"  [deactivate] subscription for {getattr(user, 'email', user.id)} stripe_sub={stripe_sub.id} (Stripe status={status})"
                )
            else:
                result["skipped"] += 1
        else:
            result["skipped"] += 1

    # Deactivate local active subscriptions with no counterpart in Stripe
    orphaned = UserSubscription.objects.filter(active=True).exclude(
        stripe_subscription_id__in=seen_stripe_ids
    )
    for local_sub in orphaned.select_related("user"):
        logger.info(
            "[PAYMENTS.FULLSYNC] %sDeactivating orphaned subscription id=%s "
            "for user_id=%s (stripe_sub=%s not found in Stripe)",
            "[DRY RUN] " if dry_run else "",
            local_sub.id,
            local_sub.user_id,
            local_sub.stripe_subscription_id,
        )
        if not dry_run:
            local_sub.deactivate()
        result["deactivated"] += 1
        result["changes"].append(
            f"  [deactivate] orphaned subscription for "
            f"{getattr(local_sub.user, 'email', local_sub.user_id)} "
            f"stripe_sub={local_sub.stripe_subscription_id} (not found in Stripe)"
        )

    return result


def run_full_sync(plans=True, customers=True, subscriptions=True, dry_run=False):
    """
    Sync the local database against the currently-configured Stripe account.
    Run this after switching between sandbox and live Stripe keys.

    Phases run in dependency order: plans → customers → subscriptions.
    With dry_run=True, fetches from Stripe and logs what would change but
    makes no database writes.

    Returns a summary dict:
        {
            "plans":         {"created": int, "updated": int, "skipped": int},
            "customers":     {"updated": int, "skipped": int},
            "subscriptions": {"created": int, "updated": int, "deactivated": int, "skipped": int},
        }
    """
    summary = {}
    if plans:
        logger.info("[PAYMENTS.FULLSYNC] Starting plan sync (dry_run=%s)", dry_run)
        summary["plans"] = _sync_plans(dry_run=dry_run)
        logger.info("[PAYMENTS.FULLSYNC] Plan sync complete: %s", summary["plans"])
    if customers:
        logger.info("[PAYMENTS.FULLSYNC] Starting customer sync (dry_run=%s)", dry_run)
        summary["customers"] = _sync_customers(dry_run=dry_run)
        logger.info(
            "[PAYMENTS.FULLSYNC] Customer sync complete: %s", summary["customers"]
        )
    if subscriptions:
        logger.info(
            "[PAYMENTS.FULLSYNC] Starting subscription sync (dry_run=%s)", dry_run
        )
        summary["subscriptions"] = _sync_subscriptions(dry_run=dry_run)
        logger.info(
            "[PAYMENTS.FULLSYNC] Subscription sync complete: %s",
            summary["subscriptions"],
        )
    return summary
