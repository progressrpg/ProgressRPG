from django.db import models
from django.conf import settings


class SubscriptionPlan(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=8, decimal_places=2)  # Eg 9.99
    interval = models.CharField(
        max_length=10, choices=[("monthly", "Monthly"), ("annual", "Annual")]
    )
    stripe_plan_id = models.CharField(max_length=100)  # ID from Stripe dashboard

    def __str__(self):
        return self.name

    @property
    def is_premium(self):
        premium_price_ids = {
            getattr(settings, "STRIPE_PRICE_ID_PREMIUM_MONTHLY", ""),
            getattr(settings, "STRIPE_PRICE_ID_PREMIUM_ANNUAL", ""),
        }
        premium_price_ids.discard("")
        return self.stripe_plan_id in premium_price_ids


class UserSubscription(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="subscriptions",
    )
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.SET_NULL, null=True)
    stripe_subscription_id = models.CharField(max_length=100, blank=True, null=True)
    active = models.BooleanField(default=False)
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField(blank=True, null=True)

    @classmethod
    def current_for_user(cls, user):
        current = (
            cls.objects.select_related("plan")
            .filter(user=user, active=True)
            .order_by("-start_date", "-id")
            .first()
        )
        if current is not None:
            return current

        return (
            cls.objects.select_related("plan")
            .filter(user=user)
            .order_by("-start_date", "-id")
            .first()
        )

    @classmethod
    def active_premium_for_user(cls, user):
        return (
            cls.objects.select_related("plan")
            .filter(user=user, active=True)
            .order_by("-start_date", "-id")
            .first()
        )

    @property
    def is_active_premium(self):
        return self.active and self.plan and self.plan.is_premium
