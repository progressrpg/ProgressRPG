from django.contrib.auth import get_user_model
from django.core import mail
from django.db import connection
from django.http import HttpResponse
from django.test import TestCase, Client, override_settings, tag
from django.test.client import RequestFactory
from django.test.utils import CaptureQueriesContext
from datetime import date, datetime, timedelta
from django.utils import timezone
from unittest.mock import patch
import logging
from types import SimpleNamespace

from allauth.core import context as allauth_context
from rest_framework.test import APIRequestFactory, force_authenticate

from api.views import MeViewSet
from api.serializers import CustomTokenObtainPairSerializer
from progress_rpg.middleware.timezone import UserTimezoneMiddleware
from users.adapters import CustomAccountAdapter
from users.achievements import achievement_goals_for_player
from users.serializers import PlayerSerializer
from gameplay.models import ActivityTimer
from users.models import Player, UserLogin
from progression.models import PlayerActivity
from users.tasks import (
    perform_account_wipe,
    reconcile_stale_online_players,
    send_email_to_users_task,
    send_rendered_email_task,
)
from users.validators import (
    PLAYER_NAME_MAX_LENGTH,
    PLAYER_NAME_MIN_LENGTH,
    generate_default_player_name,
)

from progression.day_boundaries import logical_date_for
from users.services.login_services import LOGIN_STATE_STREAK_CONTINUES, get_login_state
from users.tests import user_factory

from character.models import Character, PlayerCharacterLink
from payments.models import SubscriptionPlan, UserSubscription

logging.getLogger("general").setLevel(logging.CRITICAL)


class UserCreationTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.character = Character.objects.create(given_name="Jane", sex="Female")
        cls.user = user_factory(
            with_player=True, email="testuser@example.com", password="testpassword123"
        )

    def test_create_user(self):
        """Test that a user can be created successfully."""
        self.assertEqual(self.user.email, "testuser@example.com")
        self.assertEqual(str(self.user.timezone), "UTC")
        self.assertTrue(self.user.check_password("testpassword123"))

        player = self.user.player
        self.assertTrue(isinstance(player, Player))
        self.assertEqual(self.user, player.user)
        self.assertEqual(player.xp, 0)

    def test_create_superuser(self):
        """Test that a superuser can be created successfully."""
        User = get_user_model()
        superuser = User.objects.create_superuser(
            email="admin@example.com", password="adminpassword123"
        )
        self.assertTrue(superuser.is_superuser)
        self.assertTrue(superuser.is_staff)

    def test_player_defaults(self):
        """Test default values for a new player."""
        player = self.user.player
        self.assertEqual(player.onboarding_step, 0)
        self.assertEqual(player.total_time, 0)
        self.assertEqual(player.total_activities, 0)
        self.assertRegex(player.name, r"^player_\d{8}$")

    def test_generated_player_names_are_unique(self):
        user1 = user_factory(
            with_player=True, email="testuser3@example.com", password="testpassword123"
        )
        user2 = user_factory(
            with_player=True, email="testuser4@example.com", password="testpassword123"
        )

        self.assertNotEqual(user1.player.name, user2.player.name)

    def test_generate_default_player_name_is_stable_for_a_player_id(self):
        generated_name = generate_default_player_name(12345)

        self.assertEqual(generated_name, generate_default_player_name(12345))
        self.assertRegex(generated_name, r"^player_\d{8}$")

    def test_create_user_creates_activity_timer(self):
        """Test that a new user's player gets an ActivityTimer."""
        self.assertTrue(ActivityTimer.objects.filter(player=self.user.player).exists())

    def test_admin_created_user_gets_player_and_activity_timer(self):
        """UserAdmin.save_model() just does obj.save() - it doesn't go
        through CustomUserManager.create_user() - so CustomUserAdmin must
        explicitly run player setup for admin-created users."""
        from users.admin import CustomUserAdmin
        from django.contrib import admin as django_admin
        from users.models import CustomUser

        self.user.set_password("testpassword123")

        model_admin = CustomUserAdmin(CustomUser, django_admin.site)
        model_admin.save_model(request=None, obj=self.user, form=None, change=False)

        self.assertTrue(Player.objects.filter(user=self.user).exists())
        self.assertTrue(ActivityTimer.objects.filter(player__user=self.user).exists())


class PlayerNameValidationTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.character = Character.objects.create(given_name="Jane", sex="Female")

    def setUp(self):
        self.user = user_factory(with_player=True)

    def test_player_serializer_accepts_trimmed_valid_name(self):
        serializer = PlayerSerializer(
            self.user.player,
            data={"name": "  Red Fox-7  "},
            partial=True,
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["name"], "Red Fox-7")

    def test_player_serializer_accepts_leading_and_trailing_punctuation(self):
        serializer = PlayerSerializer(
            self.user.player,
            data={"name": "-Red Fox-"},
            partial=True,
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["name"], "-Red Fox-")

    def test_player_serializer_rejects_invalid_characters(self):
        serializer = PlayerSerializer(
            self.user.player,
            data={"name": "bad!!name"},
            partial=True,
        )

        self.assertFalse(serializer.is_valid())
        self.assertEqual(serializer.errors["name"][0], "Invalid player name.")

    def test_player_serializer_rejects_too_short_name(self):
        serializer = PlayerSerializer(
            self.user.player,
            data={"name": "ab"},
            partial=True,
        )

        self.assertFalse(serializer.is_valid())
        self.assertEqual(serializer.errors["name"][0], "Invalid player name.")

    def test_player_serializer_rejects_repeated_separators(self):
        serializer = PlayerSerializer(
            self.user.player,
            data={"name": "Red--Fox"},
            partial=True,
        )

        self.assertFalse(serializer.is_valid())
        self.assertEqual(serializer.errors["name"][0], "Invalid player name.")

    def test_player_serializer_rejects_profane_name(self):
        serializer = PlayerSerializer(
            self.user.player,
            data={"name": "fuckingwolf"},
            partial=True,
        )

        self.assertFalse(serializer.is_valid())
        self.assertEqual(serializer.errors["name"][0], "Invalid player name.")

    def test_player_serializer_rejects_leetspeak_profane_name(self):
        serializer = PlayerSerializer(
            self.user.player,
            data={"name": "sh1t-happens"},
            partial=True,
        )

        self.assertFalse(serializer.is_valid())
        self.assertEqual(serializer.errors["name"][0], "Invalid player name.")


class PlayerAchievementGoalsTest(TestCase):
    def test_new_player_gets_three_tier_one_goals(self):
        goals = achievement_goals_for_player(
            SimpleNamespace(level=0, total_time=0, total_activities=0)
        )

        self.assertEqual(
            [goal["type"] for goal in goals], ["level", "time", "activities"]
        )
        self.assertEqual([goal["tier"] for goal in goals], [1, 1, 1])
        self.assertEqual([goal["complete"] for goal in goals], [False, False, False])
        self.assertEqual([goal["threshold"] for goal in goals], [2, 1800, 5])

    def test_exact_threshold_values_advance_to_next_goal(self):
        goals = achievement_goals_for_player(
            SimpleNamespace(level=2, total_time=1800, total_activities=5)
        )

        self.assertEqual([goal["tier"] for goal in goals], [2, 2, 2])
        self.assertEqual([goal["threshold"] for goal in goals], [5, 18000, 25])
        self.assertEqual([goal["color"] for goal in goals], ["green", "green", "green"])

    def test_values_above_multiple_thresholds_show_next_unearned_goal(self):
        goals = achievement_goals_for_player(
            SimpleNamespace(level=11, total_time=80 * 60 * 60, total_activities=550)
        )

        self.assertEqual([goal["tier"] for goal in goals], [4, 5, 5])
        self.assertEqual(
            [goal["threshold"] for goal in goals],
            [20, 300 * 60 * 60, 2000],
        )
        self.assertEqual([goal["complete"] for goal in goals], [False, False, False])

    def test_completed_tier_five_stays_visible_as_complete(self):
        goals = achievement_goals_for_player(
            SimpleNamespace(
                level=50,
                total_time=300 * 60 * 60,
                total_activities=2000,
            )
        )

        self.assertEqual([goal["tier"] for goal in goals], [5, 5, 5])
        self.assertEqual([goal["complete"] for goal in goals], [True, True, True])
        self.assertEqual([goal["next_threshold"] for goal in goals], [None, None, None])

    def test_player_serializer_includes_achievements(self):
        Character.objects.create(given_name="Jane")
        user = user_factory(with_player=True)

        data = PlayerSerializer(user.player).data

        self.assertIn("achievements", data)
        self.assertEqual(len(data["achievements"]), 3)

    def test_player_serializer_reflects_trial_status(self):
        user = user_factory(with_player=True)
        plan = SubscriptionPlan.objects.create(
            name="Premium Monthly",
            description="",
            price="9.99",
            interval="monthly",
            stripe_price_id="price_serializer_trial",
        )
        future = timezone.now() + timedelta(days=5)
        UserSubscription.objects.create(
            user=user,
            plan=plan,
            active=True,
            stripe_subscription_id="sub_serializer_trial",
            trial_end=future,
        )

        data = PlayerSerializer(user.player).data

        self.assertTrue(data["is_trialing"])
        self.assertEqual(data["trial_end"], future.isoformat().replace("+00:00", "Z"))

    def test_player_serializer_not_trialing_without_subscription(self):
        user = user_factory(with_player=True)

        data = PlayerSerializer(user.player).data

        self.assertFalse(data["is_trialing"])
        self.assertIsNone(data["trial_end"])


class OnboardingTest(TestCase):
    def setUp(self):
        self.user = user_factory(with_player=True)
        self.client.login(email="testuser@example.com", password="testpassword123")
        self.player = self.user.player

    def test_initial_onboarding(self):
        """Test that onboarding starts at step 0."""
        self.assertEqual(self.user.player.onboarding_step, 0)


@tag("fast")
class PlayerMethodsTest(TestCase):
    def setUp(self):
        self.character = Character.objects.create(given_name="Jane")
        self.character2 = Character.objects.create(given_name="John")
        self.user = user_factory(with_player=True)

    def test_player_add_activity(self):
        """Test adding activity to a player."""
        player = self.user.player
        activity = PlayerActivity.objects.create(
            player=player,
            name="Test activity",
            duration=10,
        )
        activity.complete()
        self.assertEqual(player.total_time, 10)
        self.assertEqual(player.total_activities, 1)

    def test_change_character(self):
        """Test changing the character linked to a player."""
        player = self.user.player
        player.change_character(self.character2)
        link = PlayerCharacterLink.objects.filter(player=player, is_active=True).first()
        self.assertEqual(link.character, self.character2)

    def test_current_character_returns_none_without_active_link(self):
        """Player.current_character should be None if there is no active link."""
        player = self.user.player
        PlayerCharacterLink.objects.filter(player=player, is_active=True).update(
            is_active=False
        )

        self.assertIsNone(player.current_character)

    def test_register_connection_increments_and_sets_online(self):
        player = self.user.player

        self.assertEqual(player.active_connections, 0)
        self.assertFalse(player.is_online)

        player.register_connection()

        self.assertEqual(player.active_connections, 1)
        self.assertTrue(player.is_online)

    def test_unregister_connection_stays_online_with_other_connections(self):
        player = self.user.player
        player.active_connections = 2
        player.is_online = True
        player.save(update_fields=["active_connections", "is_online"])

        player.unregister_connection()

        self.assertEqual(player.active_connections, 1)
        self.assertTrue(player.is_online)

    def test_unregister_connection_transitions_offline_at_zero(self):
        player = self.user.player
        player.active_connections = 1
        player.is_online = True
        player.save(update_fields=["active_connections", "is_online"])

        player.unregister_connection()

        self.assertEqual(player.active_connections, 0)
        self.assertFalse(player.is_online)

    def test_unregister_connection_is_idempotent_at_zero(self):
        player = self.user.player
        player.active_connections = 0
        player.is_online = False
        player.save(update_fields=["active_connections", "is_online"])

        player.unregister_connection()

        self.assertEqual(player.active_connections, 0)
        self.assertFalse(player.is_online)


class UserLoginModelTest(TestCase):
    def setUp(self):
        Character.objects.create(given_name="Jane")
        self.user = user_factory(with_player=True)

    def _create_login(self, days_ago):
        # bulk_create so no post_save signal fires: the login-reward signal
        # reads and caches login stats onto self.user, and since these
        # fixture rows are created with a "now" timestamp before being
        # back-dated below, that cache would go stale for the rest of the
        # test.
        (login,) = UserLogin.objects.bulk_create([UserLogin(user=self.user)])
        timestamp = timezone.now() - timedelta(days=days_ago)
        # bulk_create skips save(), and the timestamp is rewritten after the
        # fact, so this has to stamp logical_date itself to match - leaving
        # it null would push local_date() onto its fallback, which fetches
        # the user and so breaks the query-count guarantees under test.
        UserLogin.objects.filter(pk=login.pk).update(
            timestamp=timestamp,
            logical_date=logical_date_for(self.user, timestamp),
        )
        return UserLogin.objects.get(pk=login.pk)

    def test_login_metrics_derive_from_userlogin_rows(self):
        self._create_login(3)
        self._create_login(1)
        self._create_login(0)

        self.assertEqual(self.user.days_logged_in, 3)
        self.assertEqual(self.user.current_login_streak, 2)
        self.assertEqual(self.user.max_login_streak, 2)
        self.assertEqual(self.user.total_login_events, 3)
        self.assertIsNotNone(self.user.last_recorded_login)

    def test_login_metrics_share_a_single_query_per_user(self):
        """Reading all four login metrics for one user should only hit the
        db once, since they all derive from the same cached login list."""
        self._create_login(3)
        self._create_login(1)
        self._create_login(0)

        with self.assertNumQueries(1):
            self.assertEqual(self.user.days_logged_in, 3)
            self.assertEqual(self.user.current_login_streak, 2)
            self.assertEqual(self.user.max_login_streak, 2)
            self.assertIsNotNone(self.user.last_recorded_login)

    def test_login_metrics_use_prefetched_logins_without_a_query(self):
        """When a caller (eg. the admin changelist) has already prefetched
        logins onto the user instance, no further queries should run."""
        login_a = self._create_login(3)
        login_b = self._create_login(0)
        self.user.prefetched_logins = [login_b, login_a]

        with self.assertNumQueries(0):
            self.assertEqual(self.user.days_logged_in, 2)
            self.assertEqual(self.user.current_login_streak, 1)
            self.assertEqual(self.user.total_login_events, 2)
            self.assertEqual(self.user.last_recorded_login, login_b.timestamp)

    def test_annotate_first_of_day_batches_into_one_query(self):
        """annotate_first_of_day should determine, for a batch of logins,
        which was the first of its local day using one query total - not
        one query per login (Sentry issue 118909761)."""

        def make_login(ts):
            login = UserLogin.objects.create(user=self.user)
            UserLogin.objects.filter(pk=login.pk).update(
                timestamp=ts, logical_date=logical_date_for(self.user, ts)
            )
            # select_related("user") to match real callers (eg. the admin
            # inline formset) - without it, annotate_first_of_day's access
            # of logins[0].user below would issue its own query.
            return UserLogin.objects.select_related("user").get(pk=login.pk)

        day1 = (timezone.now() - timedelta(days=1)).replace(
            hour=8, minute=0, second=0, microsecond=0
        )
        day1_early = make_login(day1)
        day1_late = make_login(day1.replace(hour=20))
        day2_only = make_login(day1 + timedelta(days=1))

        logins = [day2_only, day1_late, day1_early]

        with self.assertNumQueries(1):
            UserLogin.annotate_first_of_day(logins)

        with self.assertNumQueries(0):
            self.assertTrue(day1_early.is_first_login_of_day())
            self.assertFalse(day1_late.is_first_login_of_day())
            self.assertTrue(day2_only.is_first_login_of_day())

    def test_annotate_first_of_day_empty_list_is_a_noop(self):
        self.assertEqual(UserLogin.annotate_first_of_day([]), [])


class JwtLoginTrackingTest(TestCase):
    def setUp(self):
        Character.objects.create(given_name="Jane")
        self.user = user_factory(
            with_player=True, email="test@example.com", password="testpassword123"
        )

    def test_token_serializer_creates_user_login_record(self):
        serializer = CustomTokenObtainPairSerializer(
            data={
                "email": "test@example.com",
                "password": "testpassword123",
            }
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(UserLogin.objects.filter(user=self.user).count(), 1)


class DailyLoginRewardTest(TestCase):
    def setUp(self):
        Character.objects.create(given_name="Jane")
        self.user = user_factory(with_player=True)

    def _login_via_jwt(self):
        serializer = CustomTokenObtainPairSerializer(
            data={
                "email": self.user.email,
                "password": "testpassword123",
            }
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def _seed_login_days(self, days_ago_values):
        now = timezone.now()
        seeded_rows = UserLogin.objects.bulk_create(
            [UserLogin(user=self.user) for _ in days_ago_values]
        )
        for row, days_ago in zip(seeded_rows, days_ago_values):
            UserLogin.objects.filter(pk=row.pk).update(
                timestamp=now - timedelta(days=days_ago)
            )

    def test_first_login_of_day_rewards_10_xp(self):
        self.assertEqual(self.user.player.xp, 0)

        self._login_via_jwt()

        self.user.player.refresh_from_db()
        self.assertEqual(self.user.player.xp, 10)

    def test_streak_day_two_rewards_12_xp(self):
        # Seed only yesterday so today's login is streak day 2.
        self._seed_login_days([1])

        self._login_via_jwt()

        self.user.player.refresh_from_db()
        self.assertEqual(self.user.player.xp, 12)

    def test_streak_reset_rewards_10_xp(self):
        # Seed two days ago so the streak resets on today's login.
        self._seed_login_days([2])

        self._login_via_jwt()

        self.user.player.refresh_from_db()
        self.assertEqual(self.user.player.xp, 10)

    def test_streak_reward_is_capped_at_20_xp(self):
        # Seed a long streak up to yesterday; today's reward should cap at 20.
        self._seed_login_days(range(1, 10))

        self._login_via_jwt()

        self.user.player.refresh_from_db()
        self.assertEqual(self.user.player.xp, 20)

    def test_streak_continues_across_day_start_cutoff_same_calendar_date(self):
        # With the default 02:00 cutoff, a login at 01:00 belongs to the
        # previous logical day. A second login later the same calendar date,
        # after the cutoff, is therefore the *next* logical day - so the
        # streak should continue, not reset, even though both timestamps
        # share a calendar date (Copilot review on PR #808 caught
        # get_login_state comparing a raw calendar date against a logical
        # date here).
        day = date(2026, 8, 21)

        def seed_login(hour):
            (login,) = UserLogin.objects.bulk_create([UserLogin(user=self.user)])
            ts = timezone.make_aware(datetime(day.year, day.month, day.day, hour))
            UserLogin.objects.filter(pk=login.pk).update(
                timestamp=ts, logical_date=logical_date_for(self.user, ts)
            )
            return UserLogin.objects.get(pk=login.pk)

        seed_login(1)  # 01:00, before the cutoff -> logical date is Aug 20
        seed_login(3)  # 03:00 the same calendar date, after the cutoff -> Aug 21

        state = get_login_state(self.user)

        self.assertEqual(state["login_state"], LOGIN_STATE_STREAK_CONTINUES)
        self.assertEqual(state["login_reward_xp"], 12)


class UserTimezoneApiTest(TestCase):
    def setUp(self):
        Character.objects.create(given_name="Jane")
        self.user = user_factory(with_player=True)
        self.factory = APIRequestFactory()

    def test_me_settings_patch_updates_timezone(self):
        request = self.factory.patch(
            "/api/v1/me/settings/",
            {"timezone": "Europe/Paris"},
            format="json",
        )
        force_authenticate(request, user=self.user)

        response = MeViewSet.as_view({"patch": "user_settings"})(request)

        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(str(self.user.timezone), "Europe/Paris")
        self.assertEqual(response.data["timezone"], "Europe/Paris")


class UserTimezoneMiddlewareTest(TestCase):
    def setUp(self):
        Character.objects.create(given_name="Jane")
        self.user = user_factory(with_player=True)
        self.user.timezone = "Europe/Paris"
        self.user.save(update_fields=["timezone"])

    def tearDown(self):
        timezone.deactivate()

    def test_authenticated_request_activates_user_timezone(self):
        captured = {}

        def get_response(request):
            captured["timezone"] = str(timezone.get_current_timezone())
            return HttpResponse("ok")

        middleware = UserTimezoneMiddleware(get_response)
        request = RequestFactory().get("/")
        request.user = self.user

        response = middleware(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(captured["timezone"], "Europe/Paris")


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,  # run Celery tasks immediately, not via broker
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",  # in-memory email storage
)
class EmailTaskTest(TestCase):

    def test_send_email_task(self):
        emails = ["test@example.com"]
        subject = "Test Email"
        template_base = "emails/email_confirmation_message"
        context = {
            "user": {"email": "test@example.com"},
            "activate_url": "https://example.com/confirm/test-token",
        }
        cc_admin = False

        send_email_to_users_task.apply(
            kwargs={
                "emails": emails,
                "subject": subject,
                "template_base": template_base,
                "context": context,
                "cc_admin": cc_admin,
            }
        )

        # Check that the email was sent
        self.assertEqual(len(mail.outbox), 1)  # one email was sent
        email = mail.outbox[0]
        self.assertEqual(email.subject, subject)
        self.assertEqual(email.to, emails)
        self.assertIn("test@example.com", email.body)

    def test_send_rendered_email_task(self):
        send_rendered_email_task.apply(
            kwargs={
                "recipient_list": ["rendered@example.com"],
                "subject": "Rendered Email",
                "plain_message": "plain body",
                "html_message": "<p>html body</p>",
                "from_email": "Progress RPG <noreply@progressrpg.com>",
                "headers": {"X-Test": "1"},
            }
        )

        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.subject, "Rendered Email")
        self.assertEqual(email.to, ["rendered@example.com"])
        self.assertEqual(email.body, "plain body")
        self.assertEqual(email.extra_headers["X-Test"], "1")
        alternative = email.alternatives[0]
        alternative_content = getattr(alternative, "content", alternative[0])
        self.assertEqual(alternative_content, "<p>html body</p>")


class ReconcileStaleOnlinePlayersTest(TestCase):
    def setUp(self):
        self.user = user_factory(with_player=True)
        self.player = self.user.player

    @patch("users.tasks.async_to_sync")
    @patch("users.tasks.get_channel_layer")
    def test_resets_and_broadcasts_for_stale_connection(
        self, mock_get_channel_layer, mock_async_to_sync
    ):
        sent = []
        mock_async_to_sync.side_effect = lambda fn: (
            lambda *args, **kwargs: sent.append((args, kwargs))
        )

        self.player.active_connections = 1
        self.player.is_online = True
        self.player.last_seen = timezone.now() - timedelta(minutes=20)
        self.player.save(update_fields=["active_connections", "is_online", "last_seen"])

        reconcile_stale_online_players.apply()

        self.player.refresh_from_db(fields=["active_connections", "is_online"])
        self.assertEqual(self.player.active_connections, 0)
        self.assertFalse(self.player.is_online)

        self.assertEqual(len(sent), 1)
        (group, message), _ = sent[0]
        self.assertEqual(group, "online_users")
        self.assertEqual(message["type"], "online_count")

    @patch("users.tasks.async_to_sync")
    @patch("users.tasks.get_channel_layer")
    def test_resets_online_player_with_no_heartbeat_yet(
        self, mock_get_channel_layer, mock_async_to_sync
    ):
        mock_async_to_sync.side_effect = lambda fn: (lambda *a, **kw: None)

        self.player.active_connections = 1
        self.player.is_online = True
        self.player.last_seen = None
        self.player.save(update_fields=["active_connections", "is_online", "last_seen"])

        reconcile_stale_online_players.apply()

        self.player.refresh_from_db(fields=["active_connections", "is_online"])
        self.assertEqual(self.player.active_connections, 0)
        self.assertFalse(self.player.is_online)

    @patch("users.tasks.async_to_sync")
    @patch("users.tasks.get_channel_layer")
    def test_does_not_touch_players_with_recent_heartbeat(
        self, mock_get_channel_layer, mock_async_to_sync
    ):
        sent = []
        mock_async_to_sync.side_effect = lambda fn: (
            lambda *args, **kwargs: sent.append((args, kwargs))
        )

        self.player.active_connections = 1
        self.player.is_online = True
        self.player.last_seen = timezone.now()
        self.player.save(update_fields=["active_connections", "is_online", "last_seen"])

        reconcile_stale_online_players.apply()

        self.player.refresh_from_db(fields=["active_connections", "is_online"])
        self.assertEqual(self.player.active_connections, 1)
        self.assertTrue(self.player.is_online)
        self.assertEqual(len(sent), 0)


class PerformAccountWipeTest(TestCase):
    def setUp(self):
        self.user = user_factory(with_player=True)
        self.user.pending_delete = True
        self.user.delete_at = timezone.now() - timedelta(days=1)
        self.user.save(update_fields=["pending_delete", "delete_at"])

        self.player = self.user.player
        self.player.active_connections = 1
        self.player.is_online = True
        self.player.save(update_fields=["active_connections", "is_online"])

    def test_wiped_player_is_marked_offline(self):
        perform_account_wipe.apply()

        self.player.refresh_from_db(fields=["active_connections", "is_online"])
        self.assertEqual(self.player.active_connections, 0)
        self.assertFalse(self.player.is_online)
        self.assertNotIn(self.player, Player.get_online_players())


class CustomAccountAdapterTest(TestCase):
    def setUp(self):
        Character.objects.create(given_name="Jane")
        self.user = user_factory(with_player=True)

    @patch("users.adapters.send_rendered_email_task.delay")
    def test_send_confirmation_mail_queues_email_task(self, mock_delay):
        request = RequestFactory().get("/")
        adapter = CustomAccountAdapter()
        emailconfirmation = SimpleNamespace(
            key="confirm123",
            email_address=SimpleNamespace(user=self.user, email=self.user.email),
        )

        with allauth_context.request_context(request):
            adapter.send_confirmation_mail(request, emailconfirmation, signup=True)

        mock_delay.assert_called_once()
        kwargs = mock_delay.call_args.kwargs
        self.assertEqual(kwargs["recipient_list"], [self.user.email])
        self.assertTrue(kwargs["subject"])
        self.assertIn("/confirm_email/confirm123", kwargs["plain_message"])


class AssignCharacterTest(TestCase):
    """Tests for assign_character_to_player function"""

    def setUp(self):
        from users.utils import assign_character_to_player
        from users.models import CustomUser

        # Create available NPCs
        self.npc1 = Character.objects.create(
            given_name="Available",
            sex="Male",
        )
        self.npc2 = Character.objects.create(
            given_name="Available",
            sex="Female",
        )

        # Create a user and player
        self.user = user_factory(with_player=True)
        self.player = self.user.player

    def test_assign_character_to_player_success(self):
        """Test successful character assignment"""
        from users.utils import assign_character_to_player

        # Assign character
        character = assign_character_to_player(self.player)

        # Verify assignment
        self.assertIsNotNone(character)
        self.assertTrue(character in [self.npc1, self.npc2])

        # Verify link was created
        link = PlayerCharacterLink.objects.get(
            player=self.player, character=character, is_active=True
        )
        self.assertIsNotNone(link)

        # Verify character is no longer an NPC (has active link)
        self.assertFalse(character.is_npc)

    def test_assign_character_filters_correctly(self):
        """Test that assignment only considers valid NPCs"""
        from users.utils import assign_character_to_player

        # Create a character that's not linkable
        unlinkable = Character.objects.create(
            given_name="Unlinkable",
            sex="Male",
            is_reserved=True,
        )

        # Create a dead character
        dead = Character.objects.create(
            given_name="Dead",
            sex="Female",
            death_date=date.today(),
        )

        user2 = user_factory(
            with_player=True, email="user2@example.com", password="pass"
        )
        PlayerCharacterLink.assign_character(player=user2.player, character=self.npc1)

        # Assign character to our player
        character = assign_character_to_player(self.player)

        # Should get npc2 (only valid option)
        self.assertEqual(character, self.npc2)

        # Unlinkable and dead characters should not be assigned
        self.assertNotEqual(character, unlinkable)
        self.assertNotEqual(character, dead)

    def test_assign_character_no_available_npcs(self):
        """Test assignment when no NPCs are available"""
        from users.utils import assign_character_to_player

        user1 = user_factory(with_player=True, email="user1@test.com", password="pass")
        user2 = user_factory(with_player=True, email="user2@test.com", password="pass")
        PlayerCharacterLink.assign_character(player=user1.player, character=self.npc1)
        PlayerCharacterLink.assign_character(player=user2.player, character=self.npc2)

        # Try to assign to our player (which already has its auto-assigned character unlinked)
        character = assign_character_to_player(self.player)

        # Should return None - no available characters
        self.assertIsNone(character)


class CustomUserAdminChangelistQueryTest(TestCase):
    """Guards against the N+1 pattern in /admin/users/customuser/ (Sentry
    issue 113875738), where per-row property access on the changelist
    (player, subscription, login stats) each fired their own query.

    Rather than pin an exact query count (fragile, and not something we
    can verify without a running Django install in this environment), we
    assert the query count is the same for a small and a large number of
    users - if it scaled per row, the larger fixture would issue more
    queries.
    """

    def setUp(self):
        Character.objects.create(given_name="Jane")
        self.plan = SubscriptionPlan.objects.create(
            name="Premium", price="9.99", interval="monthly"
        )
        self.admin_user = get_user_model().objects.create_superuser(
            email="superadmin@example.com", password="testpassword123"
        )
        self.client = Client()
        self.client.force_login(self.admin_user)
        self._user_count = 0

    def _make_users(self, count):
        for _ in range(count):
            i = self._user_count
            self._user_count += 1
            user = get_user_model().objects.create_user(
                email=f"admin-list-user-{i}@example.com", password="testpassword123"
            )
            UserLogin.objects.create(user=user)
            UserLogin.objects.create(user=user)
            if i % 2 == 0:
                UserSubscription.objects.create(user=user, plan=self.plan, active=True)

    def _changelist_query_count(self):
        with CaptureQueriesContext(connection) as ctx:
            response = self.client.get("/admin/users/customuser/")
        self.assertEqual(response.status_code, 200)
        return len(ctx.captured_queries)

    def test_changelist_query_count_does_not_scale_with_user_count(self):
        self._make_users(3)
        small_count = self._changelist_query_count()

        self._make_users(20)
        large_count = self._changelist_query_count()

        self.assertEqual(
            small_count,
            large_count,
            "admin changelist query count should not grow with the number "
            "of users displayed",
        )


class CustomUserAdminChangeViewQueryTest(TestCase):
    """Guards against two N+1 patterns in
    /admin/users/customuser/{id}/change/:

    - Sentry issue 132052308: UserLoginInlineFormSet.get_queryset() rebuilt
      an un-memoized sliced queryset on every call, so Django's formset
      machinery re-ran the same "most recent 5 logins" query repeatedly
      instead of reusing one result.
    - Sentry issue 118909761: is_first_login_of_day() re-fetched the parent
      CustomUser and ran its own existence query for each of the 5
      displayed login rows.
    """

    def setUp(self):
        Character.objects.create(given_name="Jane")
        self.admin_user = get_user_model().objects.create_superuser(
            email="superadmin@example.com", password="testpassword123"
        )
        self.target_user = user_factory(with_player=True)
        for _ in range(5):
            UserLogin.objects.create(user=self.target_user)

        self.client = Client()
        self.client.force_login(self.admin_user)

    def test_change_view_queries_recent_logins_only_once(self):
        with CaptureQueriesContext(connection) as ctx:
            response = self.client.get(
                f"/admin/users/customuser/{self.target_user.pk}/change/"
            )
        self.assertEqual(response.status_code, 200)

        userlogin_queries = [
            q["sql"]
            for q in ctx.captured_queries
            if 'FROM "users_userlogin"' in q["sql"]
        ]

        # The "most recent 5 logins" fetch (ORDER BY ... DESC ... LIMIT 5)
        # should run exactly once and be reused, not re-queried per call.
        recent_logins_queries = [q for q in userlogin_queries if "DESC" in q]
        self.assertEqual(
            len(recent_logins_queries),
            1,
            "the recent-logins inline queryset should be fetched once and "
            f"reused, not re-queried per call: {recent_logins_queries}",
        )

        # is_first_login_of_day should be computed for all displayed rows in
        # one batched query, not one query per row (Sentry issue 118909761).
        first_of_day_queries = [
            q for q in userlogin_queries if q not in recent_logins_queries
        ]
        self.assertLessEqual(
            len(first_of_day_queries),
            1,
            "is_first_login_of_day should be batched into a single query "
            f"instead of one per displayed login row: {first_of_day_queries}",
        )

        # The parent CustomUser (self.user on each login row) should be
        # select_related, not re-fetched once per displayed login row.
        standalone_customuser_queries = [
            q["sql"]
            for q in ctx.captured_queries
            if 'FROM "users_customuser"' in q["sql"]
            and 'FROM "users_userlogin"' not in q["sql"]
        ]
        self.assertLessEqual(
            len(standalone_customuser_queries),
            2,
            "the parent CustomUser should not be re-fetched once per "
            f"displayed login row: {standalone_customuser_queries}",
        )
