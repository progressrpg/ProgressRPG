import json
import stripe
from django.conf import settings
from django.http import HttpResponse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
import logging

from .serializers import (
    StripeWebhookResponseSerializer,
    CreateCheckoutSessionRequestSerializer,
    CreateCheckoutSessionResponseSerializer,
)
from core.models import GameSettings
from .models import StripeEvent, SubscriptionPlan, UserSubscription
from .services import sync_subscription_from_stripe
from .webhooks import process_stripe_event

logger = logging.getLogger("general")

stripe.api_key = settings.STRIPE_SECRET_KEY


@method_decorator(csrf_exempt, name="dispatch")
class StripeWebhookView(APIView):
    permission_classes = [AllowAny]
    serializer_class = StripeWebhookResponseSerializer

    def post(self, request):
        payload = request.body
        sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")
        webhook_secret = getattr(settings, "STRIPE_WEBHOOK_SECRET", "")

        try:
            event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
        except (stripe.error.SignatureVerificationError, ValueError):
            logger.warning(
                "[PAYMENTS.WEBHOOK] Invalid Stripe webhook payload/signature"
            )
            return HttpResponse(status=400)

        obj, created = StripeEvent.objects.get_or_create(
            event_id=event.id,
            defaults={
                "event_type": event.type,
                "payload": json.loads(payload),
            },
        )

        logger.info(
            f"[PAYMENTS.WEBHOOK] Received event_id={event.id} type={event.type} "
        )

        if not created and obj.processed_at:
            logger.info(
                "[PAYMENTS.WEBHOOK] Skipping duplicate event_id=%s type=%s "
                "(already processed at %s)",
                event.id,
                event.type,
                obj.processed_at,
            )
            return HttpResponse(status=200)

        try:
            process_stripe_event(event)
            obj.event_type = event.type
            obj.payload = json.loads(payload)
            obj.processed_at = timezone.now()
            obj.processing_error = ""
            obj.save(
                update_fields=[
                    "event_type",
                    "payload",
                    "processed_at",
                    "processing_error",
                ]
            )
        except Exception as exc:
            obj.event_type = event.type
            obj.payload = json.loads(payload)
            obj.processing_error = str(exc)
            obj.save(update_fields=["event_type", "payload", "processing_error"])
            logger.exception(
                "[PAYMENTS.WEBHOOK] Failed processing event_id=%s type=%s",
                event.id,
                event.type,
            )
            return HttpResponse(status=500)

        logger.info(
            "[PAYMENTS.WEBHOOK] Processed event_id=%s type=%s created=%s",
            event.id,
            event.type,
            created,
        )

        return HttpResponse(status=200)


class CreateCheckoutSessionView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CreateCheckoutSessionResponseSerializer
    request_serializer_class = CreateCheckoutSessionRequestSerializer

    def post(self, request):
        active_subscription = UserSubscription.active_for_user(request.user)
        if active_subscription and active_subscription.is_active_premium:
            logger.info(
                "[PAYMENTS.CHECKOUT] Blocked checkout "
                f"for user_id={request.user.id} due to active premium "
                f"subscription_id={active_subscription.stripe_subscription_id}"
            )
            return Response(
                {"error": "User already has an active premium subscription."},
                status=409,
            )

        requested_plan = (request.data.get("plan") or "monthly").strip().lower()
        interval = "annual" if requested_plan == "annual" else "monthly"

        subscription_plan = SubscriptionPlan.objects.filter(interval=interval).first()

        if not subscription_plan:
            logger.error(
                "[PAYMENTS.CHECKOUT] No SubscriptionPlan found "
                f"for user_id={request.user.id} interval={interval}"
            )
            return Response(
                {"error": f"No plan configured for interval '{interval}'."},
                status=500,
            )

        premium_price_id = subscription_plan.stripe_price_id
        if not premium_price_id:
            logger.error(
                "[PAYMENTS.CHECKOUT] SubscriptionPlan has no stripe_price_id "
                f"for user_id={request.user.id} plan_id={subscription_plan.id}"
            )
            return Response(
                {"error": "Plan is not configured with a Stripe price ID."},
                status=500,
            )

        logger.info(
            "[PAYMENTS.CHECKOUT] Creating checkout session "
            f"for user_id={request.user.id} interval={interval} price_id={premium_price_id}"
        )

        success_url = getattr(settings, "STRIPE_SUCCESS_URL", "")
        cancel_url = getattr(settings, "STRIPE_CANCEL_URL", "")

        trial_period_days = GameSettings.current().trial_period_days
        offer_trial = trial_period_days > 0

        # Local UserSubscription rows are normally created by the
        # checkout.session.completed webhook. If that webhook never landed
        # (delivery failure, outage, etc.), has_previous_subscription would
        # wrongly report no prior trial. Reconcile directly against Stripe
        # before trusting the local-only result, but fail open on Stripe
        # errors so an outage doesn't block checkout entirely.
        if offer_trial and not request.user.has_previous_subscription:
            try:
                sync_subscription_from_stripe(request.user)
                request.user.refresh_from_db()
            except stripe.error.StripeError:
                logger.exception(
                    "[PAYMENTS.CHECKOUT] Stripe error verifying prior-subscription "
                    f"history for user_id={request.user.id} — falling back to local record"
                )

        offer_trial = offer_trial and not request.user.has_previous_subscription

        try:
            subscription_data = {
                "metadata": {
                    "user_id": str(request.user.id),
                    "billing_plan": "annual" if interval == "annual" else "monthly",
                },
                "trial_settings": {
                    "end_behavior": {
                        "missing_payment_method": "cancel",
                    },
                },
            }
            if offer_trial:
                subscription_data["trial_period_days"] = trial_period_days

            session_kwargs = {
                "mode": "subscription",
                "payment_method_types": ["card"],
                "payment_method_collection": "if_required",
                "client_reference_id": str(request.user.id),
                "line_items": [{"price": premium_price_id, "quantity": 1}],
                "subscription_data": subscription_data,
                "success_url": success_url,
                "cancel_url": cancel_url,
            }
            if request.user.stripe_customer_id:
                session_kwargs["customer"] = request.user.stripe_customer_id
            else:
                session_kwargs["customer_email"] = request.user.email

            try:
                session = stripe.checkout.Session.create(**session_kwargs)
            except stripe.error.InvalidRequestError as exc:
                if exc.code == "resource_missing" and exc.param == "customer":
                    # Stale customer ID (e.g. wrong Stripe environment) — clear it and retry
                    logger.warning(
                        "[PAYMENTS.CHECKOUT] Customer %s not found in Stripe, "
                        "clearing stored ID and retrying for user_id=%s",
                        request.user.stripe_customer_id,
                        request.user.id,
                    )
                    request.user.stripe_customer_id = ""
                    request.user.save(update_fields=["stripe_customer_id"])
                    session_kwargs.pop("customer", None)
                    session_kwargs["customer_email"] = request.user.email
                    session = stripe.checkout.Session.create(**session_kwargs)
                else:
                    raise

            logger.info(
                "[PAYMENTS.CHECKOUT] Created "
                f"session_id={getattr(session, 'id', None)} for user_id={request.user.id} "
                f"client_reference_id={request.user.id}"
            )
            return Response({"url": session.url})
        except stripe.error.StripeError as exc:
            logger.error(
                "[PAYMENTS.CHECKOUT] Stripe error creating checkout session "
                f"for user_id={request.user.id} interval={interval}: {exc.user_message or exc}"
            )
            return Response(
                {"error": "Unable to create checkout session."},
                status=400,
            )
        except Exception:
            logger.exception(
                "[PAYMENTS.CHECKOUT] Unexpected error creating Stripe checkout session "
                f"for user_id={request.user.id} interval={interval}"
            )
            return Response(
                {"error": "Unable to create checkout session."},
                status=400,
            )


class SyncSubscriptionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            result = sync_subscription_from_stripe(request.user)
        except stripe.error.StripeError as exc:
            logger.error(
                "[PAYMENTS.SYNC] Stripe error syncing subscription for user_id=%s: %s",
                request.user.id,
                exc,
            )
            return Response({"error": "Unable to sync subscription."}, status=502)
        return Response(result)
