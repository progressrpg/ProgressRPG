from django.contrib import admin

from payments.models import SubscriptionPlan


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ["name", "interval", "price", "stripe_plan_id"]
    list_filter = ["interval"]
    search_fields = ["name", "stripe_plan_id"]
