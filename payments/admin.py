from django.contrib import admin

from payments.models import SubscriptionPlan


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ["name", "interval", "price", "stripe_price_id"]
    list_filter = ["interval"]
    search_fields = ["name", "stripe_price_id"]
