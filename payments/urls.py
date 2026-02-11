# All non-API Django template view URLs have been removed.
# The frontend now uses REST API endpoints exclusively at /api/v1/

from django.urls import path

from payments.views import stripe_webhook

urlpatterns = [
    path("webhook/", stripe_webhook, name="stripe-webhook"),
]
