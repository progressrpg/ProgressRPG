from django.urls import path

from .views import CreateCheckoutSessionView, StripeWebhookView

urlpatterns = [
    path("webhook/", StripeWebhookView.as_view(), name="stripe-webhook"),
    path(
        "create-checkout-session/",
        CreateCheckoutSessionView.as_view(),
        name="create-checkout-session",
    ),
]
