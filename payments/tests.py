from types import SimpleNamespace
from unittest.mock import patch
from datetime import datetime, timezone

from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory
from django.test import SimpleTestCase, TestCase, override_settings

from payments.signals import provision_default_subscription
from payments.models import SubscriptionPlan, UserSubscription
from payments.services import provision_free_subscription
from payments.views import CreateCheckoutSessionView
from payments.webhooks import handle_subscription_event


class ProvisionDefaultSubscriptionSignalTests(SimpleTestCase):
    @override_settings(STRIPE_PRICE_ID_FREE="price_free", STRIPE_SECRET_KEY="sk_test")
    @patch("payments.signals.provision_free_subscription")
    def test_provisions_for_new_user_when_configured(self, mock_provision):
        user = SimpleNamespace(id=123)

        provision_default_subscription(
            sender=object,
            instance=user,
            created=True,
            raw=False,
        )

        mock_provision.assert_called_once_with(user)

    @override_settings(STRIPE_PRICE_ID_FREE="", STRIPE_SECRET_KEY="")
    @patch("payments.signals.provision_free_subscription")
    def test_skips_when_stripe_not_configured(self, mock_provision):
        user = SimpleNamespace(id=123)

        provision_default_subscription(
            sender=object,
            instance=user,
            created=True,
            raw=False,
        )

        mock_provision.assert_not_called()

    @override_settings(STRIPE_PRICE_ID_FREE="price_free", STRIPE_SECRET_KEY="sk_test")
    @patch("payments.signals.provision_free_subscription")
    def test_skips_for_existing_user_or_raw_save(self, mock_provision):
        user = SimpleNamespace(id=123)

        provision_default_subscription(
            sender=object,
            instance=user,
            created=False,
            raw=False,
        )
        provision_default_subscription(
            sender=object,
            instance=user,
            created=True,
            raw=True,
        )

        mock_provision.assert_not_called()


@override_settings(
    STRIPE_PRICE_ID_FREE="",
    STRIPE_PRICE_ID_PREMIUM_MONTHLY="price_premium_monthly",
    STRIPE_PRICE_ID_PREMIUM_ANNUAL="price_premium_annual",
)
class HandleSubscriptionEventTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="premium@example.com",
            password="testpass123",
        )
        self.free_plan = SubscriptionPlan.objects.create(
            name="Free",
            description="",
            price="0.00",
            interval="monthly",
            stripe_plan_id="price_free",
        )
        self.premium_monthly_plan = SubscriptionPlan.objects.create(
            name="Premium Monthly",
            description="",
            price="9.99",
            interval="monthly",
            stripe_plan_id="price_premium_monthly",
        )
        UserSubscription.objects.create(
            user=self.user,
            plan=self.free_plan,
            active=True,
            stripe_subscription_id="sub_free",
        )

    def test_updates_plan_from_price_object(self):
        start_ts = 1_700_000_000
        end_ts = 1_700_086_400
        handle_subscription_event(
            {
                "id": "sub_premium",
                "status": "active",
                "start_date": start_ts,
                "current_period_end": end_ts,
                "metadata": {"user_id": str(self.user.id)},
                "items": {
                    "data": [
                        {
                            "price": {
                                "id": "price_premium_monthly",
                            }
                        }
                    ]
                },
            }
        )

        subscription = UserSubscription.objects.get(
            stripe_subscription_id="sub_premium"
        )
        self.assertEqual(subscription.user, self.user)
        self.assertEqual(subscription.plan, self.premium_monthly_plan)
        self.assertEqual(
            subscription.start_date,
            datetime.fromtimestamp(start_ts, tz=timezone.utc),
        )
        self.assertEqual(
            subscription.end_date,
            datetime.fromtimestamp(end_ts, tz=timezone.utc),
        )

    def test_updates_plan_with_user_id_hint_when_metadata_missing(self):
        handle_subscription_event(
            {
                "id": "sub_premium_2",
                "status": "active",
                "metadata": {},
                "items": {
                    "data": [
                        {
                            "price": "price_premium_monthly",
                        }
                    ]
                },
            },
            user_id_hint=str(self.user.id),
        )

        subscription = UserSubscription.objects.get(
            stripe_subscription_id="sub_premium_2"
        )
        self.assertEqual(subscription.user, self.user)
        self.assertEqual(subscription.plan, self.premium_monthly_plan)


@override_settings(
    STRIPE_PRICE_ID_PREMIUM_MONTHLY="price_premium_monthly",
    STRIPE_PRICE_ID_PREMIUM_ANNUAL="price_premium_annual",
)
class CreateCheckoutSessionViewTests(TestCase):
    def test_blocks_duplicate_premium_checkout_for_active_premium_user(self):
        user = get_user_model().objects.create_user(
            email="already-premium@example.com",
            password="testpass123",
        )
        premium_plan = SubscriptionPlan.objects.create(
            name="Premium Monthly",
            description="",
            price="9.99",
            interval="monthly",
            stripe_plan_id="price_premium_monthly",
        )
        UserSubscription.objects.create(
            user=user,
            plan=premium_plan,
            active=True,
            stripe_subscription_id="sub_existing_premium",
        )

        request = APIRequestFactory().post("/payments/create-checkout-session/", {})
        request.user = user

        response = CreateCheckoutSessionView.as_view()(request)

        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            response.data["error"],
            "User already has an active premium subscription.",
        )


@override_settings(STRIPE_PRICE_ID_FREE="price_free", STRIPE_SECRET_KEY="sk_test")
class ProvisionFreeSubscriptionTests(TestCase):
    def test_returns_existing_active_premium_without_calling_stripe(self):
        user = get_user_model().objects.create_user(
            email="guarded@example.com",
            password="testpass123",
        )
        premium_plan = SubscriptionPlan.objects.create(
            name="Premium Monthly",
            description="",
            price="9.99",
            interval="monthly",
            stripe_plan_id="price_premium_monthly",
        )
        existing_subscription = UserSubscription.objects.create(
            user=user,
            plan=premium_plan,
            active=True,
            stripe_subscription_id="sub_existing_premium",
        )

        with patch("payments.services.stripe.Customer.create") as mock_customer_create:
            result = provision_free_subscription(user)

        self.assertEqual(result, existing_subscription)
        mock_customer_create.assert_not_called()
