# payments/views.py

import stripe
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .webhooks import handle_subscription_event

stripe.api_key = settings.STRIPE_SECRET_KEY


@csrf_exempt
@require_POST
def stripe_webhook(request):
    print("WEBHOOK HIT")
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")

    try:
        event = stripe.Webhook.construct_event(
            payload,
            sig_header,
            settings.STRIPE_WEBHOOK_SECRET,
        )
    except stripe.error.SignatureVerificationError as e:
        print("SIGNATURE ERROR:", str(e))
        return HttpResponse(status=400)
    except ValueError:
        print("VALUE ERROR:", str(e))
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
