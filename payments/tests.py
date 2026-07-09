from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory, force_authenticate
from django.test import SimpleTestCase, TestCase, override_settings

from payments.signals import provision_default_subscription
from payments.models import StripeEvent, SubscriptionPlan, UserSubscription
from payments.services import end_active_subscription, sync_subscription_from_stripe
from payments.views import CreateCheckoutSessionView, StripeWebhookView
from payments.webhooks import (
    handle_checkout_session_completed,
    handle_subscription_updated,
    handle_subscription_deleted,
    handle_payment_failed,
    handle_trial_will_end,
    process_stripe_event,
)


def make_event(d):
    """Recursively convert a dict to a SimpleNamespace for attribute-style access."""
    if isinstance(d, dict):
        return SimpleNamespace(**{k: make_event(v) for k, v in d.items()})
    if isinstance(d, list):
        return [make_event(item) for item in d]
    return d


class ProvisionDefaultSubscriptionSignalTests(SimpleTestCase):
    def test_does_not_provision_default_subscription_for_new_users(self):
        user = SimpleNamespace(id=123)

        provision_default_subscription(
            sender=object,
            instance=user,
            created=True,
            raw=False,
        )

        self.assertIsNone(
            provision_default_subscription(
                sender=object,
                instance=user,
                created=False,
                raw=True,
            )
        )


class HandleSubscriptionEventTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="premium@example.com",
            password="testpass123",
            stripe_customer_id="cus_test_123",
        )
        self.monthly_plan = SubscriptionPlan.objects.create(
            name="Premium Monthly",
            description="",
            price="9.99",
            interval="monthly",
            stripe_price_id="price_premium_monthly",
        )
        self.annual_plan = SubscriptionPlan.objects.create(
            name="Premium Annual",
            description="",
            price="99.00",
            interval="annual",
            stripe_price_id="price_premium_annual",
        )
        self.old_subscription = UserSubscription.objects.create(
            user=self.user,
            plan=self.monthly_plan,
            active=True,
            stripe_subscription_id="sub_old",
        )

    @patch("payments.webhooks.stripe.Subscription.retrieve")
    def test_checkout_session_completed_creates_active_subscription_and_deactivates_old(
        self, mock_retrieve
    ):
        mock_retrieve.return_value = make_event(
            {
                "id": "sub_new_123",
                "items": {"data": [{"price": {"id": "price_premium_monthly"}}]},
            }
        )
        checkout_event = make_event(
            {
                "id": "evt_checkout_1",
                "type": "checkout.session.completed",
                "data": {
                    "object": {
                        "id": "cs_test_1",
                        "customer": "cus_test_123",
                        "client_reference_id": str(self.user.id),
                        "subscription": "sub_new_123",
                    }
                },
            }
        )

        handle_checkout_session_completed(checkout_event)

        self.user.refresh_from_db()
        self.assertEqual(self.user.stripe_customer_id, "cus_test_123")

        old_subscription = UserSubscription.objects.get(
            stripe_subscription_id="sub_old"
        )
        self.assertFalse(old_subscription.active)
        self.assertIsNotNone(old_subscription.end_date)

        new_subscription = UserSubscription.objects.get(
            stripe_subscription_id="sub_new_123"
        )
        self.assertTrue(new_subscription.active)
        self.assertEqual(new_subscription.plan, self.monthly_plan)

    @patch("payments.webhooks.stripe.Subscription.retrieve")
    def test_checkout_session_completed_retrieves_subscription_for_price(
        self,
        mock_retrieve_subscription,
    ):
        checkout_event = make_event(
            {
                "id": "evt_checkout_1b",
                "type": "checkout.session.completed",
                "data": {
                    "object": {
                        "id": "cs_test_1b",
                        "customer": "cus_test_123",
                        "client_reference_id": str(self.user.id),
                        "subscription": "sub_new_1b",
                    }
                },
            }
        )

        mock_retrieve_subscription.return_value = make_event(
            {
                "id": "sub_new_1b",
                "items": {"data": [{"price": {"id": "price_premium_monthly"}}]},
            }
        )

        handle_checkout_session_completed(checkout_event)

        mock_retrieve_subscription.assert_called_once_with("sub_new_1b")
        new_subscription = UserSubscription.objects.get(
            stripe_subscription_id="sub_new_1b"
        )
        self.assertEqual(new_subscription.plan, self.monthly_plan)
        self.assertTrue(new_subscription.active)

    def test_subscription_updated_activates_and_updates_plan(self):
        subscription = UserSubscription.objects.create(
            user=self.user,
            plan=self.monthly_plan,
            active=False,
            stripe_subscription_id="sub_existing",
        )

        update_event = make_event(
            {
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
        )

        handle_subscription_updated(update_event)

        subscription.refresh_from_db()
        self.assertTrue(subscription.active)
        self.assertEqual(subscription.plan.stripe_price_id, "price_premium_annual")

    def test_subscription_deleted_deactivates_subscription(self):
        UserSubscription.deactivate_all_for_user(self.user)
        subscription = UserSubscription.objects.create(
            user=self.user,
            plan=self.monthly_plan,
            active=True,
            stripe_subscription_id="sub_delete_me",
        )

        deleted_event = make_event(
            {
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
        )

        handle_subscription_deleted(deleted_event)

        subscription.refresh_from_db()
        self.assertFalse(subscription.active)
        self.assertIsNotNone(subscription.end_date)

    def test_trial_has_ended_logged_when_status_transitions_from_trialing(self):
        UserSubscription.deactivate_all_for_user(self.user)
        subscription = UserSubscription.objects.create(
            user=self.user,
            plan=self.monthly_plan,
            active=True,
            stripe_subscription_id="sub_trial_end",
        )

        event = make_event(
            {
                "id": "evt_trial_end_1",
                "type": "customer.subscription.updated",
                "data": {
                    "object": {
                        "id": "sub_trial_end",
                        "customer": "cus_test_123",
                        "status": "active",
                        "items": {"data": [{"price": {"id": "price_premium_monthly"}}]},
                    },
                    "previous_attributes": {"status": "trialing"},
                },
            }
        )

        with self.assertLogs("general", level="INFO") as cm:
            handle_subscription_updated(event)

        self.assertTrue(
            any("Trial ended" in line for line in cm.output),
            msg=f"Expected 'Trial ended' in logs, got: {cm.output}",
        )
        subscription.refresh_from_db()
        self.assertTrue(subscription.active)

    @patch("payments.webhooks.send_trial_converted_email")
    @patch("payments.webhooks.send_trial_ended_email")
    def test_trial_ended_without_payment_sends_ended_email_only(
        self, mock_ended_email, mock_converted_email
    ):
        UserSubscription.deactivate_all_for_user(self.user)
        UserSubscription.objects.create(
            user=self.user,
            plan=self.monthly_plan,
            active=True,
            stripe_subscription_id="sub_trial_canceled",
        )

        event = make_event(
            {
                "id": "evt_trial_canceled_1",
                "type": "customer.subscription.updated",
                "data": {
                    "object": {
                        "id": "sub_trial_canceled",
                        "customer": "cus_test_123",
                        "status": "canceled",
                        "items": {"data": [{"price": {"id": "price_premium_monthly"}}]},
                    },
                    "previous_attributes": {"status": "trialing"},
                },
            }
        )

        handle_subscription_updated(event)

        mock_ended_email.assert_called_once_with(self.user)
        mock_converted_email.assert_not_called()

    @patch("payments.webhooks.send_trial_converted_email")
    @patch("payments.webhooks.send_trial_ended_email")
    def test_trial_converted_to_paid_sends_converted_email_only(
        self, mock_ended_email, mock_converted_email
    ):
        UserSubscription.deactivate_all_for_user(self.user)
        subscription = UserSubscription.objects.create(
            user=self.user,
            plan=self.monthly_plan,
            active=True,
            stripe_subscription_id="sub_trial_converted",
        )

        event = make_event(
            {
                "id": "evt_trial_converted_1",
                "type": "customer.subscription.updated",
                "data": {
                    "object": {
                        "id": "sub_trial_converted",
                        "customer": "cus_test_123",
                        "status": "active",
                        "items": {"data": [{"price": {"id": "price_premium_monthly"}}]},
                    },
                    "previous_attributes": {"status": "trialing"},
                },
            }
        )

        handle_subscription_updated(event)

        mock_converted_email.assert_called_once_with(self.user, subscription)
        mock_ended_email.assert_not_called()

    @patch("payments.webhooks.send_trial_ending_soon_email")
    def test_trial_will_end_sends_ending_soon_email_with_trial_end_date(
        self, mock_email
    ):
        UserSubscription.deactivate_all_for_user(self.user)
        UserSubscription.objects.create(
            user=self.user,
            plan=self.monthly_plan,
            active=True,
            stripe_subscription_id="sub_trial_will_end",
        )

        event = make_event(
            {
                "id": "evt_trial_will_end_1",
                "type": "customer.subscription.trial_will_end",
                "data": {
                    "object": {
                        "id": "sub_trial_will_end",
                        "customer": "cus_test_123",
                        "status": "trialing",
                        "trial_end": 1735689600,  # 2025-01-01T00:00:00Z
                        "items": {"data": [{"price": {"id": "price_premium_monthly"}}]},
                    },
                },
            }
        )

        handle_trial_will_end(event)

        self.assertEqual(mock_email.call_count, 1)
        called_user, called_trial_end = mock_email.call_args.args
        self.assertEqual(called_user, self.user)
        self.assertEqual(called_trial_end.isoformat(), "2025-01-01T00:00:00+00:00")

    @patch("payments.webhooks.send_trial_ending_soon_email")
    def test_trial_will_end_no_op_for_unknown_customer(self, mock_email):
        event = make_event(
            {
                "id": "evt_trial_will_end_unknown_1",
                "type": "customer.subscription.trial_will_end",
                "data": {
                    "object": {
                        "id": "sub_unknown",
                        "customer": "cus_does_not_exist",
                        "status": "trialing",
                        "trial_end": 1735689600,
                        "items": {"data": []},
                    },
                },
            }
        )

        handle_trial_will_end(event)

        mock_email.assert_not_called()

    def test_incomplete_status_deactivates_subscription(self):
        UserSubscription.deactivate_all_for_user(self.user)
        subscription = UserSubscription.objects.create(
            user=self.user,
            plan=self.monthly_plan,
            active=True,
            stripe_subscription_id="sub_incomplete",
        )

        event = make_event(
            {
                "id": "evt_incomplete_1",
                "type": "customer.subscription.updated",
                "data": {
                    "object": {
                        "id": "sub_incomplete",
                        "customer": "cus_test_123",
                        "status": "incomplete",
                        "items": {"data": [{"price": {"id": "price_premium_monthly"}}]},
                    },
                    "previous_attributes": {},
                },
            }
        )

        handle_subscription_updated(event)

        subscription.refresh_from_db()
        self.assertFalse(subscription.active)

    def test_unhandled_event_type_logs_info(self):
        event = make_event(
            {
                "id": "evt_unknown_1",
                "type": "payment_intent.created",
            }
        )

        with self.assertLogs("general", level="INFO") as cm:
            process_stripe_event(event)

        self.assertTrue(
            any("Unhandled event" in line for line in cm.output),
            msg=f"Expected 'Unhandled event' in logs, got: {cm.output}",
        )

    @patch("payments.webhooks.stripe.Subscription.retrieve")
    def test_payment_failed_retrieves_unexpanded_subscription(self, mock_retrieve):
        mock_retrieve.return_value = make_event(
            {
                "id": "sub_payment_failed",
                "items": {"data": [{"price": {"id": "price_premium_monthly"}}]},
            }
        )
        UserSubscription.deactivate_all_for_user(self.user)
        UserSubscription.objects.create(
            user=self.user,
            plan=self.monthly_plan,
            active=True,
            stripe_subscription_id="sub_payment_failed",
        )

        event = make_event(
            {
                "id": "evt_payment_failed_1",
                "type": "invoice.payment_failed",
                "data": {
                    "object": {
                        "id": "in_test_1",
                        "customer": "cus_test_123",
                        # subscription is a bare string (unexpanded)
                        "subscription": "sub_payment_failed",
                    }
                },
            }
        )

        with self.assertLogs("general", level="WARNING") as cm:
            handle_payment_failed(event)

        mock_retrieve.assert_called_once_with("sub_payment_failed")
        self.assertTrue(
            any("Payment failed" in line for line in cm.output),
            msg=f"Expected 'Payment failed' in logs, got: {cm.output}",
        )


class UserPremiumPropertyTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="premium-property@example.com",
            password="testpass123",
        )
        self.plan = SubscriptionPlan.objects.create(
            name="Premium Monthly",
            description="",
            price="9.99",
            interval="monthly",
            stripe_price_id="price_premium_monthly",
        )

    def test_returns_false_without_active_subscription(self):
        self.assertFalse(self.user.is_premium)

    def test_returns_false_for_inactive_subscription(self):
        UserSubscription.objects.create(
            user=self.user,
            plan=self.plan,
            active=False,
            stripe_subscription_id="sub_inactive",
        )

        self.assertFalse(self.user.is_premium)

    def test_returns_true_for_active_subscription(self):
        UserSubscription.objects.create(
            user=self.user,
            plan=self.plan,
            active=True,
            stripe_subscription_id="sub_active",
        )

        self.assertTrue(self.user.is_premium)


class ProcessStripeEventRoutingTests(SimpleTestCase):
    @patch("payments.webhooks.handle_checkout_session_completed")
    def test_routes_checkout_completed_events(self, mock_checkout):
        event = SimpleNamespace(type="checkout.session.completed")

        process_stripe_event(event)

        mock_checkout.assert_called_once_with(event)

    @patch("payments.webhooks.handle_trial_will_end")
    def test_routes_trial_will_end_events(self, mock_trial_will_end):
        event = SimpleNamespace(type="customer.subscription.trial_will_end")

        process_stripe_event(event)

        mock_trial_will_end.assert_called_once_with(event)


@override_settings(STRIPE_WEBHOOK_SECRET="whsec_test")
class StripeWebhookViewTests(TestCase):
    def test_deduplicates_events_by_event_id(self):
        event = make_event(
            {
                "id": "evt_dupe_1",
                "type": "customer.subscription.deleted",
                "data": {
                    "object": {
                        "id": "sub_123",
                        "customer": "cus_123",
                    }
                },
            }
        )

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
        event = make_event(
            {
                "id": "evt_success_1",
                "type": "customer.subscription.updated",
                "data": {"object": {"id": "sub_1", "customer": "cus_1"}},
            }
        )

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
        event = make_event(
            {
                "id": "evt_fail_then_retry_1",
                "type": "customer.subscription.deleted",
                "data": {"object": {"id": "sub_2", "customer": "cus_2"}},
            }
        )

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


class CreateCheckoutSessionViewTests(TestCase):
    def setUp(self):
        self.monthly_plan = SubscriptionPlan.objects.create(
            name="Premium Monthly",
            description="",
            price="9.99",
            interval="monthly",
            stripe_price_id="price_premium_monthly",
        )
        self.annual_plan = SubscriptionPlan.objects.create(
            name="Premium Annual",
            description="",
            price="99.00",
            interval="annual",
            stripe_price_id="price_premium_annual",
        )

    def test_blocks_duplicate_premium_checkout_for_active_premium_user(self):
        user = get_user_model().objects.create_user(
            email="already-premium@example.com",
            password="testpass123",
        )
        UserSubscription.objects.create(
            user=user,
            plan=self.monthly_plan,
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

        mock_create_session.return_value = SimpleNamespace(
            url="https://checkout.example/session",
            id="cs_test_annual",
        )

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
        self.assertEqual(create_kwargs["customer_email"], "annual@example.com")
        self.assertNotIn("customer", create_kwargs)

    @override_settings(
        STRIPE_SUCCESS_URL="https://example.com/success",
        STRIPE_CANCEL_URL="https://example.com/cancel",
    )
    @patch("payments.views.stripe.checkout.Session.create")
    @patch("payments.views.GameSettings.current")
    def test_includes_trial_for_new_user_with_trial_configured(
        self, mock_game_settings, mock_create_session
    ):
        mock_game_settings.return_value.trial_period_days = 7
        user = get_user_model().objects.create_user(
            email="new-trial@example.com",
            password="testpass123",
        )

        mock_create_session.return_value = SimpleNamespace(
            url="https://checkout.example/session",
            id="cs_test_trial_new",
        )

        request = APIRequestFactory().post(
            "/payments/create-checkout-session/",
            {"plan": "monthly"},
            format="json",
        )
        force_authenticate(request, user=user)

        response = CreateCheckoutSessionView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        create_kwargs = mock_create_session.call_args.kwargs
        self.assertEqual(create_kwargs["subscription_data"]["trial_period_days"], 7)

    @override_settings(
        STRIPE_SUCCESS_URL="https://example.com/success",
        STRIPE_CANCEL_URL="https://example.com/cancel",
    )
    @patch("payments.views.stripe.checkout.Session.create")
    @patch("payments.views.GameSettings.current")
    def test_suppresses_trial_for_returning_subscriber(
        self, mock_game_settings, mock_create_session
    ):
        mock_game_settings.return_value.trial_period_days = 7
        user = get_user_model().objects.create_user(
            email="returning@example.com",
            password="testpass123",
        )
        # Returning user: has a past (inactive) subscription
        UserSubscription.objects.create(
            user=user,
            plan=self.monthly_plan,
            active=False,
            stripe_subscription_id="sub_old_cancelled",
        )

        mock_create_session.return_value = SimpleNamespace(
            url="https://checkout.example/session",
            id="cs_test_no_trial",
        )

        request = APIRequestFactory().post(
            "/payments/create-checkout-session/",
            {"plan": "monthly"},
            format="json",
        )
        force_authenticate(request, user=user)

        response = CreateCheckoutSessionView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        create_kwargs = mock_create_session.call_args.kwargs
        self.assertNotIn("trial_period_days", create_kwargs["subscription_data"])

    @override_settings(
        STRIPE_SUCCESS_URL="https://example.com/success",
        STRIPE_CANCEL_URL="https://example.com/cancel",
    )
    @patch("payments.views.stripe.checkout.Session.create")
    def test_reuses_existing_customer_for_checkout(self, mock_create_session):
        user = get_user_model().objects.create_user(
            email="existing-customer@example.com",
            password="testpass123",
            stripe_customer_id="cus_existing_123",
        )

        mock_create_session.return_value = SimpleNamespace(
            url="https://checkout.example/session",
            id="cs_test_existing_customer",
        )

        request = APIRequestFactory().post(
            "/payments/create-checkout-session/",
            {"plan": "monthly"},
            format="json",
        )
        force_authenticate(request, user=user)

        response = CreateCheckoutSessionView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        create_kwargs = mock_create_session.call_args.kwargs
        self.assertEqual(create_kwargs["customer"], "cus_existing_123")
        self.assertNotIn("customer_email", create_kwargs)

    @override_settings(
        STRIPE_SUCCESS_URL="https://example.com/success",
        STRIPE_CANCEL_URL="https://example.com/cancel",
    )
    @patch("payments.views.stripe.checkout.Session.create")
    @patch("payments.views.GameSettings.current")
    @patch("payments.views.sync_subscription_from_stripe")
    def test_reconciles_with_stripe_before_offering_trial_when_no_local_record(
        self, mock_sync, mock_game_settings, mock_create_session
    ):
        """
        A user whose checkout.session.completed webhook never landed has no
        local UserSubscription row, but did previously trial. The view should
        ask Stripe directly (via sync_subscription_from_stripe) rather than
        trusting the empty local record.
        """
        mock_game_settings.return_value.trial_period_days = 7
        user = get_user_model().objects.create_user(
            email="webhook-missed@example.com",
            password="testpass123",
        )

        def fake_sync(synced_user):
            UserSubscription.objects.create(
                user=synced_user,
                plan=self.monthly_plan,
                active=False,
                stripe_subscription_id="sub_backfilled",
            )
            return {"status": "canceled", "synced": True}

        mock_sync.side_effect = fake_sync
        mock_create_session.return_value = SimpleNamespace(
            url="https://checkout.example/session",
            id="cs_test_reconciled",
        )

        request = APIRequestFactory().post(
            "/payments/create-checkout-session/",
            {"plan": "monthly"},
            format="json",
        )
        force_authenticate(request, user=user)

        response = CreateCheckoutSessionView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        mock_sync.assert_called_once()
        create_kwargs = mock_create_session.call_args.kwargs
        self.assertNotIn("trial_period_days", create_kwargs["subscription_data"])

    @override_settings(
        STRIPE_SUCCESS_URL="https://example.com/success",
        STRIPE_CANCEL_URL="https://example.com/cancel",
    )
    @patch("payments.views.stripe.checkout.Session.create")
    @patch("payments.views.GameSettings.current")
    @patch("payments.views.sync_subscription_from_stripe")
    def test_offers_trial_when_stripe_reconciliation_finds_no_prior_subscription(
        self, mock_sync, mock_game_settings, mock_create_session
    ):
        mock_game_settings.return_value.trial_period_days = 7
        mock_sync.return_value = {"status": "none", "synced": True}
        user = get_user_model().objects.create_user(
            email="genuinely-new@example.com",
            password="testpass123",
        )

        mock_create_session.return_value = SimpleNamespace(
            url="https://checkout.example/session",
            id="cs_test_genuine_new",
        )

        request = APIRequestFactory().post(
            "/payments/create-checkout-session/",
            {"plan": "monthly"},
            format="json",
        )
        force_authenticate(request, user=user)

        response = CreateCheckoutSessionView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        mock_sync.assert_called_once()
        create_kwargs = mock_create_session.call_args.kwargs
        self.assertEqual(create_kwargs["subscription_data"]["trial_period_days"], 7)

    @override_settings(
        STRIPE_SUCCESS_URL="https://example.com/success",
        STRIPE_CANCEL_URL="https://example.com/cancel",
    )
    @patch("payments.views.stripe.checkout.Session.create")
    @patch("payments.views.GameSettings.current")
    @patch("payments.views.sync_subscription_from_stripe")
    def test_fails_open_to_local_record_when_stripe_reconciliation_errors(
        self, mock_sync, mock_game_settings, mock_create_session
    ):
        import stripe

        mock_game_settings.return_value.trial_period_days = 7
        mock_sync.side_effect = stripe.error.APIConnectionError("boom")
        user = get_user_model().objects.create_user(
            email="stripe-down@example.com",
            password="testpass123",
        )

        mock_create_session.return_value = SimpleNamespace(
            url="https://checkout.example/session",
            id="cs_test_stripe_down",
        )

        request = APIRequestFactory().post(
            "/payments/create-checkout-session/",
            {"plan": "monthly"},
            format="json",
        )
        force_authenticate(request, user=user)

        response = CreateCheckoutSessionView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        create_kwargs = mock_create_session.call_args.kwargs
        self.assertEqual(create_kwargs["subscription_data"]["trial_period_days"], 7)

    @override_settings(
        STRIPE_SUCCESS_URL="https://example.com/success",
        STRIPE_CANCEL_URL="https://example.com/cancel",
    )
    @patch("payments.views.stripe.checkout.Session.create")
    @patch("payments.views.GameSettings.current")
    @patch("payments.views.sync_subscription_from_stripe")
    def test_skips_stripe_reconciliation_when_local_record_already_exists(
        self, mock_sync, mock_game_settings, mock_create_session
    ):
        mock_game_settings.return_value.trial_period_days = 7
        user = get_user_model().objects.create_user(
            email="already-has-local-record@example.com",
            password="testpass123",
        )
        UserSubscription.objects.create(
            user=user,
            plan=self.monthly_plan,
            active=False,
            stripe_subscription_id="sub_old_local",
        )

        mock_create_session.return_value = SimpleNamespace(
            url="https://checkout.example/session",
            id="cs_test_skip_sync",
        )

        request = APIRequestFactory().post(
            "/payments/create-checkout-session/",
            {"plan": "monthly"},
            format="json",
        )
        force_authenticate(request, user=user)

        response = CreateCheckoutSessionView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        mock_sync.assert_not_called()


class HasPreviousSubscriptionTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="prev-sub@example.com",
            password="testpass123",
        )
        self.plan = SubscriptionPlan.objects.create(
            name="Premium Monthly",
            description="",
            price="9.99",
            interval="monthly",
            stripe_price_id="price_monthly_prev",
        )

    def test_false_when_no_subscriptions(self):
        self.assertFalse(self.user.has_previous_subscription)

    def test_true_when_inactive_subscription_exists(self):
        UserSubscription.objects.create(
            user=self.user,
            plan=self.plan,
            active=False,
            stripe_subscription_id="sub_cancelled",
        )
        self.assertTrue(self.user.has_previous_subscription)

    def test_true_when_active_subscription_exists(self):
        UserSubscription.objects.create(
            user=self.user,
            plan=self.plan,
            active=True,
            stripe_subscription_id="sub_active",
        )
        self.assertTrue(self.user.has_previous_subscription)


class EndActiveSubscriptionTests(TestCase):
    def test_returns_none_without_active_subscription(self):
        user = get_user_model().objects.create_user(
            email="no-active-subscription@example.com",
            password="testpass123",
        )

        with patch("payments.services.stripe.Subscription.cancel") as mock_cancel:
            result = end_active_subscription(user)

        self.assertIsNone(result)
        mock_cancel.assert_not_called()

    @patch("payments.services.stripe.Subscription.cancel")
    def test_cancels_active_subscription_and_deactivates_it(self, mock_cancel):
        user = get_user_model().objects.create_user(
            email="premium-downgrade@example.com",
            password="testpass123",
        )
        plan = SubscriptionPlan.objects.create(
            name="Premium Monthly",
            description="",
            price="9.99",
            interval="monthly",
            stripe_price_id="price_premium_monthly",
        )
        existing_subscription = UserSubscription.objects.create(
            user=user,
            plan=plan,
            active=True,
            stripe_subscription_id="sub_existing_premium",
        )

        result = end_active_subscription(user)

        self.assertEqual(result, existing_subscription)
        existing_subscription.refresh_from_db()
        self.assertFalse(existing_subscription.active)
        self.assertIsNotNone(existing_subscription.end_date)


def make_stripe_subscription(sub_id, status, price_id=None, ended_at=None):
    price = SimpleNamespace(id=price_id) if price_id else None
    item = SimpleNamespace(price=price, plan=None)
    return SimpleNamespace(
        id=sub_id,
        status=status,
        items=SimpleNamespace(data=[item]),
        ended_at=ended_at,
        canceled_at=None,
    )


class SyncSubscriptionBackfillTests(TestCase):
    """
    Covers #506: has_previous_subscription must not depend solely on the
    checkout.session.completed webhook having landed. sync_subscription_from_stripe
    should backfill local rows for any subscription Stripe knows about, including
    past/cancelled ones that never got a local record.
    """

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="backfill@example.com",
            password="testpass123",
            stripe_customer_id="cus_backfill_123",
        )
        self.plan = SubscriptionPlan.objects.create(
            name="Premium Monthly",
            description="",
            price="9.99",
            interval="monthly",
            stripe_price_id="price_backfill_monthly",
        )

    @patch("payments.services.stripe.Subscription.list")
    def test_backfills_local_record_for_past_subscription_missing_webhook(
        self, mock_list
    ):
        mock_list.return_value = SimpleNamespace(
            data=[
                make_stripe_subscription(
                    "sub_past_trial",
                    "canceled",
                    price_id="price_backfill_monthly",
                    ended_at=1700000000,
                )
            ]
        )

        self.assertFalse(self.user.has_previous_subscription)

        result = sync_subscription_from_stripe(self.user)

        self.assertEqual(result["status"], "canceled")
        self.assertTrue(self.user.has_previous_subscription)
        local_sub = UserSubscription.objects.get(
            stripe_subscription_id="sub_past_trial"
        )
        self.assertFalse(local_sub.active)
        self.assertEqual(local_sub.plan, self.plan)
        self.assertIsNotNone(local_sub.end_date)

    @patch("payments.services.stripe.Subscription.list")
    def test_backfills_historical_subscriptions_alongside_an_active_candidate(
        self, mock_list
    ):
        mock_list.return_value = SimpleNamespace(
            data=[
                make_stripe_subscription(
                    "sub_current_active",
                    "active",
                    price_id="price_backfill_monthly",
                ),
                make_stripe_subscription(
                    "sub_old_trial",
                    "canceled",
                    price_id="price_backfill_monthly",
                    ended_at=1650000000,
                ),
            ]
        )

        sync_subscription_from_stripe(self.user)

        self.assertTrue(
            UserSubscription.objects.filter(
                stripe_subscription_id="sub_current_active", active=True
            ).exists()
        )
        self.assertTrue(
            UserSubscription.objects.filter(
                stripe_subscription_id="sub_old_trial", active=False
            ).exists()
        )

    @patch("payments.services.stripe.Subscription.list")
    def test_does_not_duplicate_existing_local_record_on_backfill(self, mock_list):
        UserSubscription.objects.create(
            user=self.user,
            plan=self.plan,
            active=False,
            stripe_subscription_id="sub_already_local",
        )
        mock_list.return_value = SimpleNamespace(
            data=[
                make_stripe_subscription(
                    "sub_already_local",
                    "canceled",
                    price_id="price_backfill_monthly",
                )
            ]
        )

        sync_subscription_from_stripe(self.user)

        self.assertEqual(
            UserSubscription.objects.filter(
                stripe_subscription_id="sub_already_local"
            ).count(),
            1,
        )
