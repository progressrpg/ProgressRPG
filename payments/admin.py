import logging

import stripe
from django.contrib import admin, messages

from payments.models import SubscriptionPlan, UserSubscription, StripeEvent
from payments.services import end_active_subscription_and_activate_free

logger = logging.getLogger(__name__)


@admin.register(StripeEvent)
class StripeEventAdmin(admin.ModelAdmin):
    list_display = [
        "event_id",
        "event_type",
        "created_at",
        "processed_at",
        "processing_error",
    ]
    search_fields = ["event_id", "event_type"]
    list_filter = ["event_type", "created_at", "processed_at", "processing_error"]
    readonly_fields = [
        "event_id",
        "event_type",
        "payload",
        "created_at",
        "processed_at",
        "processing_error",
    ]


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ["name", "interval", "price", "stripe_price_id"]
    list_filter = ["interval"]
    search_fields = ["name", "stripe_price_id"]


@admin.register(UserSubscription)
class UserSubscriptionAdmin(admin.ModelAdmin):
    list_display = ["user", "plan", "active", "start_date", "end_date"]
    list_filter = ["active", "plan__name"]
    search_fields = ["user__email", "plan__name", "stripe_subscription_id"]
    actions = ["end_subscription_and_activate_free"]

    @admin.action(description="End active subscription and activate free plan")
    def end_subscription_and_activate_free(self, request, queryset):
        success_count = 0
        skip_count = 0

        for subscription in queryset.select_related("user", "plan"):
            if not subscription.active:
                skip_count += 1
                continue

            try:
                end_active_subscription_and_activate_free(subscription.user)
                success_count += 1
            except stripe.error.StripeError as exc:
                logger.warning(
                    "Stripe error when downgrading user %s: %s",
                    subscription.user_id,
                    exc,
                )
                self.message_user(
                    request,
                    f"Stripe error for {subscription.user}: {exc}",
                    level=messages.WARNING,
                )
            except Exception as exc:
                logger.exception(
                    "Failed to downgrade user %s: %s",
                    subscription.user_id,
                    exc,
                )
                self.message_user(
                    request,
                    f"Failed to downgrade {subscription.user}: {exc}",
                    level=messages.ERROR,
                )

        if success_count:
            self.message_user(
                request,
                f"Successfully ended subscription and activated free plan for {success_count} user(s).",
                level=messages.SUCCESS,
            )
        if skip_count:
            self.message_user(
                request,
                f"{skip_count} subscription(s) skipped — already inactive.",
                level=messages.WARNING,
            )
