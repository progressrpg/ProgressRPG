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
from .webhooks import handle_subscription_event

logger = logging.getLogger(__name__)

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
            return HttpResponse(status=400)

        event_type = event.get("type")
        data = event.get("data", {}).get("object", {})

        if event_type in {
            "customer.subscription.created",
            "customer.subscription.updated",
            "customer.subscription.deleted",
        }:
            handle_subscription_event(data)

        return HttpResponse(status=200)


class CreateCheckoutSessionView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CreateCheckoutSessionResponseSerializer
    request_serializer_class = CreateCheckoutSessionRequestSerializer

    def post(self, request):
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

        if not premium_price_id:
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
            return Response({"url": session.url})
        except Exception as exc:
            logger.exception("Error creating Stripe checkout session")
            return Response(
                {"error": "Unable to create checkout session."},
                status=400,
            )
