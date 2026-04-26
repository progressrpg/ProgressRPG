from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from payments.models import SubscriptionPlan, UserSubscription


@override_settings(
    STRIPE_PRICE_ID_FREE="",
    STRIPE_PRICE_ID_PREMIUM_MONTHLY="price_premium_monthly",
    STRIPE_PRICE_ID_PREMIUM_ANNUAL="price_premium_annual",
)
class ActivityTimerPremiumRewardTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="premium-timer@example.com",
            password="testpass123",
        )
        self.player = self.user.player

    def grant_premium(self):
        UserSubscription.deactivate_all_for_user(self.user)
        premium_plan = SubscriptionPlan.objects.create(
            name="Premium Monthly",
            description="",
            price="9.99",
            interval="monthly",
            stripe_price_id="price_premium_monthly",
        )
        return UserSubscription.objects.create(
            user=self.user,
            plan=premium_plan,
            active=True,
            stripe_subscription_id=f"sub_timer_{self.user.id}",
        )

    def test_timer_completion_returns_premium_reward_breakdown(self):
        self.grant_premium()
        timer = self.player.activity_timer
        timer.new_activity("Premium focus")
        timer.elapsed_time = 60
        timer.save(update_fields=["elapsed_time"])

        completion = timer.complete()

        self.player.refresh_from_db()
        self.assertEqual(
            completion,
            {
                "duration_seconds": 60,
                "base_xp": 60,
                "xp_multiplier": 2,
                "xp_gained": 120,
                "level_ups": [1],
            },
        )
        self.assertEqual(self.player.level, 1)
        self.assertEqual(self.player.xp, 20)
