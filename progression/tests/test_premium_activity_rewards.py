from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from payments.models import SubscriptionPlan, UserSubscription
from progression.models import PlayerActivity


@override_settings(
    STRIPE_PRICE_ID_FREE="",
    STRIPE_PRICE_ID_PREMIUM_MONTHLY="price_premium_monthly",
    STRIPE_PRICE_ID_PREMIUM_ANNUAL="price_premium_annual",
)
class PlayerActivityPremiumRewardTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="premium-activity@example.com",
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
            stripe_subscription_id=f"sub_premium_{self.user.id}",
        )

    def test_non_premium_activity_reward_uses_base_xp(self):
        activity = PlayerActivity.objects.create(
            player=self.player,
            name="Write tests",
            duration=60,
        )

        reward_summary = activity.get_xp_reward_summary()

        self.assertEqual(
            reward_summary,
            {
                "duration_seconds": 60,
                "base_xp": 60,
                "xp_multiplier": 1,
                "xp_gained": 60,
            },
        )
        self.assertEqual(activity.complete(), 60)

    def test_premium_activity_reward_doubles_xp(self):
        self.grant_premium()
        activity = PlayerActivity.objects.create(
            player=self.player,
            name="Write tests",
            duration=60,
        )

        reward_summary = activity.get_xp_reward_summary()

        self.assertEqual(
            reward_summary,
            {
                "duration_seconds": 60,
                "base_xp": 60,
                "xp_multiplier": 2,
                "xp_gained": 120,
            },
        )
        self.assertEqual(activity.complete(), 120)
