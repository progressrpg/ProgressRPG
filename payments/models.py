from django.db import models
from django.conf import settings


# Create your models here.
class SubscriptionPlan(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=8, decimal_places=2)  # Eg 9.99
    interval = models.CharField(
        max_length=10, choices=[("monthly", "Monthly"), ("yearly", "Yearly")]
    )
    stripe_plan_id = models.CharField(max_length=100)  # ID from Stripe dashboard

    def __str__(self):
        return self.name


class UserSubscription(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.SET_NULL, null=True)
    stripe_subscription_id = models.CharField(max_length=100, blank=True, null=True)
    active = models.BooleanField(default=False)
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField(blank=True, null=True)
