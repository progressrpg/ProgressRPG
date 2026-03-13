import stripe
from django.conf import settings
from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response

from .webhooks import handle_subscription_event

stripe.api_key = settings.STRIPE_SECRET_KEY


@method_decorator(csrf_exempt, name="dispatch")
class StripeWebhookView(APIView):
    permission_classes = [AllowAny]

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

    def post(self, request):
        premium_price_id = (
            getattr(settings, "STRIPE_PRICE_ID_PREMIUM_MONTHLY", "") or ""
        )

        if not premium_price_id:
            return Response(
                {"error": "Missing STRIPE_PRICE_ID_PREMIUM_MONTHLY setting."},
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
                subscription_data={"metadata": {"user_id": str(request.user.id)}},
                success_url=success_url,
                cancel_url=cancel_url,
            )
            return Response({"url": session.url})
        except Exception as exc:
            return Response({"error": str(exc)}, status=400)
