from decimal import Decimal
from unittest.mock import patch, PropertyMock

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase, TestCase, override_settings
from django.contrib import admin as django_admin
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from django.utils import timezone

from core.checks import REQUIRED_PROD_SETTINGS, check_required_prod_settings
from core.admin import AnnouncementAdmin, FeatureFlagForm
from core.models import Announcement, FeatureFlag, GameSettings
from users.services.login_services import (
    calculate_daily_login_reward,
    LOGIN_STATE_ALREADY_LOGGED_TODAY,
    LOGIN_STATE_STREAK_CONTINUES,
    LOGIN_STATE_STREAK_RESET,
)

User = get_user_model()

from users.tests import user_factory


class GameSettingsSingletonTest(TestCase):
    def setUp(self):
        GameSettings.objects.all().delete()

    def test_current_creates_instance_on_first_call(self):
        self.assertEqual(GameSettings.objects.count(), 0)
        settings = GameSettings.current()
        self.assertIsNotNone(settings)
        self.assertEqual(GameSettings.objects.count(), 1)

    def test_current_returns_same_instance(self):
        s1 = GameSettings.current()
        s2 = GameSettings.current()
        self.assertEqual(s1.pk, s2.pk)

    def test_defaults(self):
        s = GameSettings.current()
        self.assertEqual(s.free_timer_limit_seconds, 1800)
        self.assertEqual(s.daily_login_base_xp, 10)
        self.assertEqual(s.daily_login_streak_step_xp, 2)
        self.assertEqual(s.daily_login_max_xp, 20)
        self.assertEqual(s.premium_activity_xp_multiplier, Decimal("2.00"))
        self.assertEqual(s.default_activity_xp_per_second, Decimal("1.0000"))
        self.assertEqual(s.registration_cap, 1_000_000_000)


class GameSettingsValidationTest(TestCase):
    def setUp(self):
        GameSettings.objects.all().delete()
        self.settings = GameSettings.current()

    def test_negative_free_timer_limit_rejected(self):
        self.settings.free_timer_limit_seconds = -1
        with self.assertRaises(ValidationError):
            self.settings.save()

    def test_negative_base_xp_rejected(self):
        self.settings.daily_login_base_xp = -1
        with self.assertRaises(ValidationError):
            self.settings.save()

    def test_max_xp_below_base_xp_rejected(self):
        self.settings.daily_login_base_xp = 15
        self.settings.daily_login_max_xp = 10
        with self.assertRaises(ValidationError):
            self.settings.save()

    def test_zero_multiplier_rejected(self):
        self.settings.premium_activity_xp_multiplier = Decimal("0")
        with self.assertRaises(ValidationError):
            self.settings.save()

    def test_negative_xp_per_second_rejected(self):
        self.settings.default_activity_xp_per_second = Decimal("-0.5")
        with self.assertRaises(ValidationError):
            self.settings.save()

    def test_negative_registration_cap_rejected(self):
        self.settings.registration_cap = -1
        with self.assertRaises(ValidationError):
            self.settings.save()

    def test_duplicate_instance_rejected(self):
        with self.assertRaises(ValidationError):
            GameSettings.objects.create()


class GameSettingsCapIncreaseTriggerTest(TestCase):
    def setUp(self):
        GameSettings.objects.all().delete()
        self.settings = GameSettings.current()
        self.settings.registration_cap = 10
        self.settings.save()

    @patch("users.tasks.invite_waitlist_entries.delay")
    def test_increasing_cap_enqueues_invite_task(self, mock_delay):
        self.settings.registration_cap = 20
        with self.captureOnCommitCallbacks(execute=True):
            self.settings.save()
        mock_delay.assert_called_once()

    @patch("users.tasks.invite_waitlist_entries.delay")
    def test_decreasing_cap_does_not_enqueue(self, mock_delay):
        self.settings.registration_cap = 5
        with self.captureOnCommitCallbacks(execute=True):
            self.settings.save()
        mock_delay.assert_not_called()

    @patch("users.tasks.invite_waitlist_entries.delay")
    def test_unchanged_cap_does_not_enqueue(self, mock_delay):
        with self.captureOnCommitCallbacks(execute=True):
            self.settings.save()
        mock_delay.assert_not_called()

    @patch("users.tasks.invite_waitlist_entries.delay")
    def test_first_creation_does_not_enqueue(self, mock_delay):
        GameSettings.objects.all().delete()
        with self.captureOnCommitCallbacks(execute=True):
            GameSettings.current()
        mock_delay.assert_not_called()

    @patch("users.tasks.invite_waitlist_entries.delay")
    def test_failed_validation_does_not_enqueue(self, mock_delay):
        self.settings.registration_cap = -1
        with self.assertRaises(ValidationError):
            with self.captureOnCommitCallbacks(execute=True):
                self.settings.save()
        mock_delay.assert_not_called()


class LoginRewardFromSettingsTest(TestCase):
    def setUp(self):
        GameSettings.objects.all().delete()
        self.settings = GameSettings.current()

    def test_no_reward_for_already_logged_today(self):
        self.assertEqual(
            calculate_daily_login_reward(LOGIN_STATE_ALREADY_LOGGED_TODAY, streak=5),
            0,
        )

    def test_base_xp_on_streak_reset(self):
        self.settings.daily_login_base_xp = 10
        self.settings.save()
        self.assertEqual(
            calculate_daily_login_reward(LOGIN_STATE_STREAK_RESET, streak=1),
            10,
        )

    def test_streak_bonus_applied(self):
        self.settings.daily_login_base_xp = 10
        self.settings.daily_login_streak_step_xp = 2
        self.settings.daily_login_max_xp = 20
        self.settings.save()
        # streak=3 → bonus = (3-1)*2 = 4 → total = 14
        self.assertEqual(
            calculate_daily_login_reward(LOGIN_STATE_STREAK_CONTINUES, streak=3),
            14,
        )

    def test_streak_reward_capped_at_max(self):
        self.settings.daily_login_base_xp = 10
        self.settings.daily_login_streak_step_xp = 5
        self.settings.daily_login_max_xp = 20
        self.settings.save()
        # streak=100 → would be huge, but capped at 20
        self.assertEqual(
            calculate_daily_login_reward(LOGIN_STATE_STREAK_CONTINUES, streak=100),
            20,
        )

    def test_custom_base_xp_used(self):
        self.settings.daily_login_base_xp = 25
        self.settings.daily_login_max_xp = 50
        self.settings.save()
        self.assertEqual(
            calculate_daily_login_reward(LOGIN_STATE_STREAK_RESET, streak=1),
            25,
        )


class PremiumXpMultiplierFromSettingsTest(TestCase):
    def setUp(self):
        GameSettings.objects.all().delete()
        self.settings = GameSettings.current()
        self.user = user_factory(with_player=True)

    def test_free_player_gets_1x(self):
        with patch.object(
            User, "is_premium", new_callable=PropertyMock, return_value=False
        ):
            multiplier = self.user.player.get_activity_xp_multiplier()
        self.assertEqual(multiplier, Decimal("1.0"))

    def test_premium_player_uses_configured_multiplier(self):
        self.settings.premium_activity_xp_multiplier = Decimal("3.00")
        self.settings.save()
        with patch.object(
            User, "is_premium", new_callable=PropertyMock, return_value=True
        ):
            multiplier = self.user.player.get_activity_xp_multiplier()
        self.assertEqual(multiplier, Decimal("3.00"))

    def test_premium_player_uses_default_multiplier(self):
        with patch.object(
            User, "is_premium", new_callable=PropertyMock, return_value=True
        ):
            multiplier = self.user.player.get_activity_xp_multiplier()
        self.assertEqual(multiplier, Decimal("2.00"))


class GameSettingsAPITest(APITestCase):
    def setUp(self):
        GameSettings.objects.all().delete()
        GameSettings.current()
        self.user = user_factory()
        self.client.force_authenticate(user=self.user)

    def test_game_settings_endpoint_returns_all_fields(self):
        res = self.client.get("/api/v1/game_settings/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.json()
        self.assertIn("free_timer_limit_seconds", data)
        self.assertIn("daily_login_base_xp", data)
        self.assertIn("daily_login_streak_step_xp", data)
        self.assertIn("daily_login_max_xp", data)
        self.assertIn("premium_activity_xp_multiplier", data)
        self.assertIn("default_activity_xp_per_second", data)

    def test_game_settings_requires_auth(self):
        self.client.force_authenticate(user=None)
        res = self.client.get("/api/v1/game_settings/")
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class RequiredProdSettingsCheckTest(SimpleTestCase):
    def all_settings_present(self):
        return {name: "set" for name, _hint in REQUIRED_PROD_SETTINGS}

    def test_passes_when_all_settings_present(self):
        with override_settings(**self.all_settings_present()):
            errors = check_required_prod_settings(app_configs=None)
        self.assertEqual(errors, [])

    def test_reports_error_for_each_missing_setting(self):
        overrides = self.all_settings_present()
        overrides.update(SECRET_KEY="", STRIPE_SECRET_KEY="")
        with override_settings(**overrides):
            errors = check_required_prod_settings(app_configs=None)
        messages = [error.msg for error in errors]
        self.assertEqual(len(errors), 2)
        self.assertIn("settings.SECRET_KEY is not set.", messages)
        self.assertIn("settings.STRIPE_SECRET_KEY is not set.", messages)

    def test_error_ids_are_scoped_to_core(self):
        overrides = self.all_settings_present()
        overrides.update(DATABASE_URL="")
        with override_settings(**overrides):
            errors = check_required_prod_settings(app_configs=None)
        self.assertEqual(errors[0].id, "core.E001")


_FAKE_FEATURE_FLAGS_TS = """
const featureFlags = {
  activityList: ['all'],
  tasksFeature: ['testers'],
  categoriesFeature: [],
  skillsFeature: [],
  projectsFeature: [],
};
"""


@patch("core.admin._FEATURE_FLAGS_TS")
class FeatureFlagFormKeyChoicesTests(TestCase):
    def test_excludes_keys_already_created(self, mock_path):
        mock_path.read_text.return_value = _FAKE_FEATURE_FLAGS_TS
        FeatureFlag.objects.create(key="tasksFeature", access_groups=["testers"])

        form = FeatureFlagForm()

        choice_keys = [key for key, _ in form.fields["key"].choices]
        self.assertNotIn("tasksFeature", choice_keys)
        self.assertIn("activityList", choice_keys)
        self.assertIn("categoriesFeature", choice_keys)

    def test_editing_existing_flag_keeps_its_own_key_selectable(self, mock_path):
        mock_path.read_text.return_value = _FAKE_FEATURE_FLAGS_TS
        flag = FeatureFlag.objects.create(key="tasksFeature", access_groups=["testers"])
        FeatureFlag.objects.create(key="activityList", access_groups=["all"])

        form = FeatureFlagForm(instance=flag)

        choice_keys = [key for key, _ in form.fields["key"].choices]
        self.assertIn("tasksFeature", choice_keys)
        self.assertNotIn("activityList", choice_keys)


class AnnouncementSaveTest(TestCase):
    def test_publishing_sets_published_at_if_unset(self):
        announcement = Announcement.objects.create(
            title="Hi", body="Body", is_published=True
        )
        self.assertIsNotNone(announcement.published_at)

    def test_publishing_does_not_overwrite_existing_published_at(self):
        original = timezone.now() - timezone.timedelta(days=3)
        announcement = Announcement.objects.create(
            title="Hi", body="Body", is_published=True, published_at=original
        )
        self.assertEqual(announcement.published_at, original)

    def test_creating_unpublished_leaves_published_at_unset(self):
        announcement = Announcement.objects.create(
            title="Hi", body="Body", is_published=False
        )
        self.assertIsNone(announcement.published_at)

    def test_saving_again_after_publish_does_not_change_published_at(self):
        announcement = Announcement.objects.create(
            title="Hi", body="Body", is_published=True
        )
        first_published_at = announcement.published_at

        announcement.title = "Updated"
        announcement.save()

        self.assertEqual(announcement.published_at, first_published_at)


class AnnouncementAdminReadonlyFieldsTest(TestCase):
    def setUp(self):
        self.admin = AnnouncementAdmin(Announcement, django_admin.site)

    def test_published_at_editable_when_unset(self):
        announcement = Announcement.objects.create(title="Hi", body="Body")
        self.assertNotIn(
            "published_at", self.admin.get_readonly_fields(None, announcement)
        )

    def test_published_at_readonly_once_set(self):
        announcement = Announcement.objects.create(
            title="Hi", body="Body", is_published=True
        )
        self.assertIn(
            "published_at", self.admin.get_readonly_fields(None, announcement)
        )

    def test_published_at_editable_for_new_unsaved_announcement(self):
        self.assertNotIn("published_at", self.admin.get_readonly_fields(None, None))
