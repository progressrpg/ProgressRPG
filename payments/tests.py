from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory, force_authenticate
from django.test import SimpleTestCase, TestCase, override_settings

from payments.signals import provision_default_subscription
from payments.models import StripeEvent, SubscriptionPlan, UserSubscription
from payments.services import provision_free_subscription
from payments.views import CreateCheckoutSessionView, StripeWebhookView
from payments.webhooks import (
    handle_checkout_session_completed,
    handle_subscription_updated,
    handle_subscription_deleted,
    process_stripe_event,
)


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
            stripe_customer_id="cus_test_123",
        )
        self.free_plan = SubscriptionPlan.objects.create(
            name="Free",
            description="",
            price="0.00",
            interval="monthly",
            stripe_price_id="price_free",
        )
        self.premium_monthly_plan = SubscriptionPlan.objects.create(
            name="Premium Monthly",
            description="",
            price="9.99",
            interval="monthly",
            stripe_price_id="price_premium_monthly",
        )
        self.premium_annual_plan = SubscriptionPlan.objects.create(
            name="Premium Annual",
            description="",
            price="99.00",
            interval="annual",
            stripe_price_id="price_premium_annual",
        )
        UserSubscription.objects.create(
            user=self.user,
            plan=self.free_plan,
            active=True,
            stripe_subscription_id="sub_free",
        )

    def test_checkout_session_completed_creates_active_subscription_and_deactivates_old(
        self,
    ):
        checkout_event = {
            "id": "evt_checkout_1",
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_test_1",
                    "customer": "cus_test_123",
                    "client_reference_id": str(self.user.id),
                    "subscription": "sub_new_123",
                    "subscription_details": {
                        "items": {
                            "data": [
                                {
                                    "price": {
                                        "id": "price_premium_monthly",
                                    }
                                }
                            ]
                        }
                    },
                }
            },
        }

        handle_checkout_session_completed(checkout_event)

        self.user.refresh_from_db()
        self.assertEqual(self.user.stripe_customer_id, "cus_test_123")

        old_subscription = UserSubscription.objects.get(
            stripe_subscription_id="sub_free"
        )
        self.assertFalse(old_subscription.active)
        self.assertIsNotNone(old_subscription.end_date)

        new_subscription = UserSubscription.objects.get(
            stripe_subscription_id="sub_new_123"
        )
        self.assertTrue(new_subscription.active)
        self.assertEqual(new_subscription.plan, self.premium_monthly_plan)

    @patch("payments.webhooks.stripe.Subscription.retrieve")
    def test_checkout_session_completed_fetches_subscription_when_price_missing(
        self,
        mock_retrieve_subscription,
    ):
        checkout_event = {
            "id": "evt_checkout_missing_price_1",
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_test_missing_price_1",
                    "customer": "cus_test_123",
                    "client_reference_id": str(self.user.id),
                    "subscription": "sub_new_missing_price_1",
                    "subscription_details": {},
                }
            },
        }

        mock_retrieve_subscription.return_value = {
            "id": "sub_new_missing_price_1",
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

        handle_checkout_session_completed(checkout_event)

        mock_retrieve_subscription.assert_called_once_with("sub_new_missing_price_1")
        new_subscription = UserSubscription.objects.get(
            stripe_subscription_id="sub_new_missing_price_1"
        )
        self.assertEqual(new_subscription.plan, self.premium_monthly_plan)
        self.assertTrue(new_subscription.active)

    def test_subscription_updated_activates_and_updates_plan(self):
        subscription = UserSubscription.objects.create(
            user=self.user,
            plan=self.premium_monthly_plan,
            active=False,
            stripe_subscription_id="sub_existing",
        )

        update_event = {
            "id": "evt_sub_update_1",
            "type": "customer.subscription.updated",
            "data": {
                "object": {
                    "id": "sub_existing",
                    "customer": "cus_test_123",
                    "status": "active",
                    "items": {
                        "data": [
                            {
                                "price": {
                                    "id": "price_premium_annual",
                                }
                            }
                        ]
                    },
                }
            },
        }

        handle_subscription_updated(update_event)

        subscription.refresh_from_db()
        self.assertTrue(subscription.active)
        self.assertEqual(subscription.plan.stripe_price_id, "price_premium_annual")

    def test_subscription_deleted_deactivates_subscription(self):
        subscription = UserSubscription.objects.create(
            user=self.user,
            plan=self.premium_monthly_plan,
            active=True,
            stripe_subscription_id="sub_delete_me",
        )

        deleted_event = {
            "id": "evt_sub_delete_1",
            "type": "customer.subscription.deleted",
            "data": {
                "object": {
                    "id": "sub_delete_me",
                    "customer": "cus_test_123",
                    "status": "canceled",
                }
            },
        }

        handle_subscription_deleted(deleted_event)

        subscription.refresh_from_db()
        self.assertFalse(subscription.active)
        self.assertIsNotNone(subscription.end_date)


class ProcessStripeEventRoutingTests(SimpleTestCase):
    @patch("payments.webhooks.handle_checkout_session_completed")
    def test_routes_checkout_completed_events(self, mock_checkout):
        event = {"type": "checkout.session.completed", "data": {"object": {}}}

        process_stripe_event(event)

        mock_checkout.assert_called_once_with(event)


@override_settings(STRIPE_WEBHOOK_SECRET="whsec_test")
class StripeWebhookViewTests(TestCase):
    def test_deduplicates_events_by_event_id(self):
        event = {
            "id": "evt_dupe_1",
            "type": "customer.subscription.deleted",
            "data": {
                "object": {
                    "id": "sub_123",
                    "customer": "cus_123",
                }
            },
        }

        request_factory = APIRequestFactory()
        view = StripeWebhookView.as_view()

        with (
            patch("payments.views.stripe.Webhook.construct_event", return_value=event),
            patch("payments.views.process_stripe_event") as mock_process,
        ):
            response_1 = view(
                request_factory.post(
                    "/payments/webhook/",
                    data=b"{}",
                    content_type="application/json",
                    HTTP_STRIPE_SIGNATURE="sig",
                )
            )
            response_2 = view(
                request_factory.post(
                    "/payments/webhook/",
                    data=b"{}",
                    content_type="application/json",
                    HTTP_STRIPE_SIGNATURE="sig",
                )
            )

        self.assertEqual(response_1.status_code, 200)
        self.assertEqual(response_2.status_code, 200)
        self.assertEqual(StripeEvent.objects.filter(event_id="evt_dupe_1").count(), 1)
        mock_process.assert_called_once_with(event)

    def test_returns_400_for_invalid_signature_or_payload(self):
        request_factory = APIRequestFactory()
        view = StripeWebhookView.as_view()

        with patch(
            "payments.views.stripe.Webhook.construct_event", side_effect=ValueError
        ):
            response = view(
                request_factory.post(
                    "/payments/webhook/",
                    data=b"{}",
                    content_type="application/json",
                    HTTP_STRIPE_SIGNATURE="invalid",
                )
            )

        self.assertEqual(response.status_code, 400)

    def test_records_event_type_and_processed_at_on_success(self):
        event = {
            "id": "evt_success_1",
            "type": "customer.subscription.updated",
            "data": {"object": {"id": "sub_1", "customer": "cus_1"}},
        }

        request_factory = APIRequestFactory()
        view = StripeWebhookView.as_view()

        with (
            patch("payments.views.stripe.Webhook.construct_event", return_value=event),
            patch("payments.views.process_stripe_event") as mock_process,
        ):
            response = view(
                request_factory.post(
                    "/payments/webhook/",
                    data=b"{}",
                    content_type="application/json",
                    HTTP_STRIPE_SIGNATURE="sig",
                )
            )

        self.assertEqual(response.status_code, 200)
        mock_process.assert_called_once_with(event)

        stripe_event = StripeEvent.objects.get(event_id="evt_success_1")
        self.assertEqual(stripe_event.event_type, "customer.subscription.updated")
        self.assertIsNotNone(stripe_event.processed_at)
        self.assertEqual(stripe_event.processing_error, "")

    def test_records_processing_error_and_retries_unprocessed_event(self):
        event = {
            "id": "evt_fail_then_retry_1",
            "type": "customer.subscription.deleted",
            "data": {"object": {"id": "sub_2", "customer": "cus_2"}},
        }

        request_factory = APIRequestFactory()
        view = StripeWebhookView.as_view()

        with patch("payments.views.stripe.Webhook.construct_event", return_value=event):
            with patch(
                "payments.views.process_stripe_event",
                side_effect=RuntimeError("boom"),
            ):
                response_fail = view(
                    request_factory.post(
                        "/payments/webhook/",
                        data=b"{}",
                        content_type="application/json",
                        HTTP_STRIPE_SIGNATURE="sig",
                    )
                )

            with patch("payments.views.process_stripe_event") as mock_process_retry:
                response_retry = view(
                    request_factory.post(
                        "/payments/webhook/",
                        data=b"{}",
                        content_type="application/json",
                        HTTP_STRIPE_SIGNATURE="sig",
                    )
                )

        self.assertEqual(response_fail.status_code, 500)
        self.assertEqual(response_retry.status_code, 200)
        mock_process_retry.assert_called_once_with(event)

        stripe_event = StripeEvent.objects.get(event_id="evt_fail_then_retry_1")
        self.assertEqual(stripe_event.event_type, "customer.subscription.deleted")
        self.assertIsNotNone(stripe_event.processed_at)
        self.assertEqual(stripe_event.processing_error, "")


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
            stripe_price_id="price_premium_monthly",
        )
        UserSubscription.objects.create(
            user=user,
            plan=premium_plan,
            active=True,
            stripe_subscription_id="sub_existing_premium",
        )

        request = APIRequestFactory().post("/payments/create-checkout-session/", {})
        force_authenticate(request, user=user)

        response = CreateCheckoutSessionView.as_view()(request)

        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            response.data["error"],
            "User already has an active premium subscription.",
        )

    @override_settings(
        STRIPE_SUCCESS_URL="https://example.com/success",
        STRIPE_CANCEL_URL="https://example.com/cancel",
    )
    @patch("payments.views.stripe.checkout.Session.create")
    def test_creates_checkout_session_for_annual_plan(self, mock_create_session):
        user = get_user_model().objects.create_user(
            email="annual@example.com",
            password="testpass123",
        )

        session = SimpleNamespace(url="https://checkout.example/session")
        session.get = lambda key, default=None: (
            "cs_test_annual" if key == "id" else default
        )
        mock_create_session.return_value = session

        request = APIRequestFactory().post(
            "/payments/create-checkout-session/",
            {"plan": "annual"},
            format="json",
        )
        force_authenticate(request, user=user)

        response = CreateCheckoutSessionView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["url"], "https://checkout.example/session")

        mock_create_session.assert_called_once()
        create_kwargs = mock_create_session.call_args.kwargs
        self.assertEqual(
            create_kwargs["line_items"][0]["price"], "price_premium_annual"
        )
        self.assertEqual(
            create_kwargs["subscription_data"]["metadata"]["billing_plan"],
            "annual",
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
            stripe_price_id="price_premium_monthly",
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

    @patch("payments.services.stripe.Subscription.create")
    @patch("payments.services.stripe.Customer.create")
    def test_persists_new_customer_id_and_reuses_it_for_subscription(
        self,
        mock_customer_create,
        mock_subscription_create,
    ):
        user = get_user_model().objects.create_user(
            email="new-free@example.com",
            password="testpass123",
            stripe_customer_id="",
        )
        SubscriptionPlan.objects.create(
            name="Free",
            description="",
            price="0.00",
            interval="monthly",
            stripe_price_id="price_free",
        )

        mock_customer_create.return_value = SimpleNamespace(id="cus_new_123")
        mock_subscription_create.return_value = SimpleNamespace(
            id="sub_free_123",
            status="active",
        )

        result = provision_free_subscription(user)

        user.refresh_from_db()
        self.assertEqual(user.stripe_customer_id, "cus_new_123")
        self.assertTrue(result.active)
        self.assertEqual(result.plan.stripe_price_id, "price_free")

        mock_customer_create.assert_called_once()
        mock_subscription_create.assert_called_once()
        self.assertEqual(
            mock_subscription_create.call_args.kwargs["customer"],
            "cus_new_123",
        )

    @patch("payments.services.stripe.Subscription.create")
    @patch("payments.services.stripe.Customer.create")
    def test_reuses_existing_customer_id_without_creating_customer(
        self,
        mock_customer_create,
        mock_subscription_create,
    ):
        user = get_user_model().objects.create_user(
            email="existing-customer@example.com",
            password="testpass123",
            stripe_customer_id="cus_existing_123",
        )
        SubscriptionPlan.objects.create(
            name="Free",
            description="",
            price="0.00",
            interval="monthly",
            stripe_price_id="price_free",
        )

        mock_subscription_create.return_value = SimpleNamespace(
            id="sub_free_existing_customer",
            status="active",
        )

        provision_free_subscription(user)

        mock_customer_create.assert_not_called()
        mock_subscription_create.assert_called_once()
        self.assertEqual(
            mock_subscription_create.call_args.kwargs["customer"],
            "cus_existing_123",
        )

    @patch("payments.services.stripe.Subscription.create")
    @patch("payments.services.stripe.Customer.create")
    def test_deactivates_previous_active_subscription_with_end_date(
        self,
        mock_customer_create,
        mock_subscription_create,
    ):
        user = get_user_model().objects.create_user(
            email="rollover@example.com",
            password="testpass123",
            stripe_customer_id="",
        )
        free_plan = SubscriptionPlan.objects.create(
            name="Free",
            description="",
            price="0.00",
            interval="monthly",
            stripe_price_id="price_free",
        )
        old_subscription = UserSubscription.objects.create(
            user=user,
            plan=free_plan,
            active=True,
            stripe_subscription_id="sub_old",
        )

        mock_customer_create.return_value = SimpleNamespace(id="cus_rollover")
        mock_subscription_create.return_value = SimpleNamespace(
            id="sub_new_rollover",
            status="active",
        )

        with patch(
            "payments.services.UserSubscription.current_for_user", return_value=None
        ):
            new_subscription = provision_free_subscription(user)

        old_subscription.refresh_from_db()
        new_subscription.refresh_from_db()
        self.assertFalse(old_subscription.active)
        self.assertIsNotNone(old_subscription.end_date)
        self.assertTrue(new_subscription.active)
        self.assertIsNone(new_subscription.end_date)

    def test_raises_when_free_plan_is_missing(self):
        user = get_user_model().objects.create_user(
            email="missing-plan@example.com",
            password="testpass123",
            stripe_customer_id="",
        )

        with self.assertRaisesMessage(ValueError, "No SubscriptionPlan configured"):
            provision_free_subscription(user)
