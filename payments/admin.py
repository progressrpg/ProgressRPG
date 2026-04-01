from django.contrib import admin

from payments.models import SubscriptionPlan, UserSubscription, StripeEvent


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
