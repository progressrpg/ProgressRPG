# payments/views.py

import stripe
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from users.models import CustomUser as User
from .webhooks import handle_subscription_event

stripe.api_key = settings.STRIPE_SECRET_KEY


@csrf_exempt
@require_POST
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")

    try:
        event = stripe.Webhook.construct_event(
            payload,
            sig_header,
            settings.STRIPE_WEBHOOK_SECRET,
        )
    except stripe.error.SignatureVerificationError:
        return HttpResponse(status=400)
    except ValueError:
        return HttpResponse(status=400)

    event_type = event["type"]
    data = event["data"]["object"]

    if event_type in [
        "customer.subscription.created",
        "customer.subscription.updated",
        "customer.subscription.deleted",
    ]:
        handle_subscription_event(data)

    return HttpResponse(status=200)


@login_required
@csrf_exempt
def create_checkout_session(request):
    user = User.objects.get(id=request.user.id)

    if not user.stripe_customer_id:
        from .services import provision_free_subscription

        provision_free_subscription(user)

    try:
        session = stripe.checkout.Session.create(
            customer=user.stripe_customer_id,
            payment_method_types=["card"],
            line_items=[
                {"price": settings.STRIPE_PREMIUM_MONTHLY_PRICE_ID, "quantity": 1}
            ],
            mode="subscription",
            success_url=settings.STRIPE_SUCCESS_URL,
            cancel_url=settings.STRIPE_CANCEL_URL,
        )
        return JsonResponse({"url": session.url})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)
