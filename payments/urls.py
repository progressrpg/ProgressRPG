# All non-API Django template view URLs have been removed.
# The frontend now uses REST API endpoints exclusively at /api/v1/

from django.urls import path

from .views import stripe_webhook, create_checkout_session

urlpatterns = [
    path("webhook/", stripe_webhook, name="stripe-webhook"),
    path(
        "create-checkout-session/",
        create_checkout_session,
        name="create-checkout-session",
    ),
]
