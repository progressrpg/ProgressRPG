import stripe
from django.conf import settings
from django.http import HttpResponse
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
from .models import UserSubscription
from .webhooks import handle_checkout_session_completed, handle_subscription_event

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

        event_type = event.get("type")
        data = event.get("data", {}).get("object", {})
        logger.info(
            "[PAYMENTS.WEBHOOK] Received event type=%s event_id=%s object_id=%s",
            event_type,
            event.get("id"),
            data.get("id"),
        )

        if event_type in {
            "customer.subscription.created",
            "customer.subscription.updated",
            "customer.subscription.deleted",
        }:
            handle_subscription_event(data)
        elif event_type == "checkout.session.completed":
            handle_checkout_session_completed(data)
        else:
            logger.info(
                "[PAYMENTS.WEBHOOK] Ignoring unhandled event type=%s",
                event_type,
            )

        return HttpResponse(status=200)


class CreateCheckoutSessionView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CreateCheckoutSessionResponseSerializer
    request_serializer_class = CreateCheckoutSessionRequestSerializer

    def post(self, request):
        active_subscription = UserSubscription.active_premium_for_user(request.user)
        if active_subscription and active_subscription.is_active_premium:
            logger.info(
                "[PAYMENTS.CHECKOUT] Blocked checkout for user_id=%s due to active premium subscription_id=%s",
                request.user.id,
                active_subscription.stripe_subscription_id,
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
            "[PAYMENTS.CHECKOUT] Creating checkout session for user_id=%s plan=%s price_id=%s",
            request.user.id,
            plan,
            premium_price_id,
        )

        if not premium_price_id:
            logger.error(
                "[PAYMENTS.CHECKOUT] Missing Stripe price id for user_id=%s selected_plan=%s",
                request.user.id,
                requested_plan,
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
                "[PAYMENTS.CHECKOUT] Created session_id=%s for user_id=%s client_reference_id=%s",
                session.get("id"),
                request.user.id,
                str(request.user.id),
            )
            return Response({"url": session.url})
        except Exception:
            logger.exception(
                "[PAYMENTS.CHECKOUT] Error creating Stripe checkout session for user_id=%s plan=%s",
                request.user.id,
                plan,
            )
            return Response(
                {"error": "Unable to create checkout session."},
                status=400,
            )
