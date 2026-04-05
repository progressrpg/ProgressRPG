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
from .models import StripeEvent, UserSubscription
from .webhooks import process_stripe_event

logger = logging.getLogger("django")

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
            event_id=event.get("id"),
            defaults={
                "event_type": event.get("type"),
                "payload": event,
            },
        )

        logger.info(
            f"[PAYMENTS.WEBHOOK] Received event_id={event.get('id')} type={event.get('type')} "
        )

        # Already-processed events are safe to ignore.
        if not created and obj.processed_at:
            return HttpResponse(status=200)

        try:
            process_stripe_event(event)
            obj.event_type = event.get("type")
            obj.payload = event
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
            obj.event_type = event.get("type")
            obj.payload = event
            obj.processing_error = str(exc)
            obj.save(update_fields=["event_type", "payload", "processing_error"])
            logger.exception(
                "[PAYMENTS.WEBHOOK] Failed processing event_id=%s type=%s",
                event.get("id"),
                event.get("type"),
            )
            return HttpResponse(status=500)

        logger.info(
            f"[PAYMENTS.WEBHOOK] object created={created} existing_processed_at={obj.processed_at} existing_error={obj.processing_error}"
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
        plan = "annual" if requested_plan == "annual" else requested_plan

        price_id_by_plan = {
            "monthly": getattr(settings, "STRIPE_PRICE_ID_PREMIUM_MONTHLY", "") or "",
            "annual": getattr(settings, "STRIPE_PRICE_ID_PREMIUM_ANNUAL", "") or "",
        }

        if plan not in price_id_by_plan:
            return Response(
                {"error": "Invalid plan. Expected 'monthly' or 'annual'."},
                status=400,
            )

        premium_price_id = price_id_by_plan[plan]
        logger.info(
            "[PAYMENTS.CHECKOUT] Creating checkout session "
            f"for user_id={request.user.id} plan={plan} price_id={premium_price_id}"
        )

        if not premium_price_id:
            logger.error(
                "[PAYMENTS.CHECKOUT] Missing Stripe price id "
                f"for user_id={request.user.id} selected_plan={requested_plan}"
            )
            return Response(
                {
                    "error": (
                        "Missing STRIPE price setting for selected plan "
                        f"'{requested_plan}'."
                    )
                },
                status=500,
            )

        success_url = getattr(settings, "STRIPE_SUCCESS_URL", "")
        cancel_url = getattr(settings, "STRIPE_CANCEL_URL", "")

        try:
            session = stripe.checkout.Session.create(
                mode="subscription",
                payment_method_types=["card"],
                customer_email=request.user.email,
                client_reference_id=str(request.user.id),
                line_items=[{"price": premium_price_id, "quantity": 1}],
                subscription_data={
                    "metadata": {
                        "user_id": str(request.user.id),
                        "billing_plan": "annual" if plan == "annual" else "monthly",
                    },
                    "trial_period_days": 30,
                    "trial_settings": {
                        "end_behavior": {
                            "missing_payment_method": "cancel",
                        },
                    },
                },
                success_url=success_url,
                cancel_url=cancel_url,
            )
            logger.info(
                "[PAYMENTS.CHECKOUT] Created "
                f"session_id={session.get('id')} for user_id={request.user.id} "
                f"client_reference_id={request.user.id}"
            )
            return Response({"url": session.url})
        except Exception:
            logger.exception(
                "[PAYMENTS.CHECKOUT] Error creating Stripe checkout session "
                f"for user_id={request.user.id} plan={plan}"
            )
            return Response(
                {"error": "Unable to create checkout session."},
                status=400,
            )
