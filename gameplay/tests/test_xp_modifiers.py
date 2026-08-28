from datetime import timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.test import TestCase
from django.utils import timezone

from character.models import Character, PlayerCharacterLink
from gameplay.models import XpModifier
from gameplay.services import xp_modifiers as xpm
from progression.models import ActivityDefinition, CharacterActivity

from users.tests import user_factory


def _linked_player_and_character():
    user = user_factory(with_player=True)
    player = user.player
    character = Character.objects.create(given_name="Hero")
    link = PlayerCharacterLink.objects.create(player=player, character=character)
    return player, character, link


class ActivateLinkModifierTests(TestCase):
    def setUp(self):
        self.player, self.character, self.link = _linked_player_and_character()

    def test_defaults_to_character_scope(self):
        mod = xpm.activate_link_modifier(
            link=self.link, key="test_key", multiplier=Decimal("1.5")
        )
        self.assertEqual(mod.scope, XpModifier.Scope.CHARACTER)
        self.assertEqual(mod.character_id, self.character.id)
        self.assertIsNone(mod.player_id)
        self.assertTrue(mod.is_active)
        self.assertIsNone(mod.ends_at)

    def test_can_target_player_scope(self):
        mod = xpm.activate_link_modifier(
            link=self.link,
            key="test_key",
            multiplier=Decimal("1.25"),
            scope=XpModifier.Scope.PLAYER,
        )
        self.assertEqual(mod.scope, XpModifier.Scope.PLAYER)
        self.assertEqual(mod.player_id, self.player.id)
        self.assertIsNone(mod.character_id)

    def test_second_call_updates_same_row_instead_of_duplicating(self):
        first = xpm.activate_link_modifier(
            link=self.link, key="test_key", multiplier=Decimal("1.5")
        )
        second = xpm.activate_link_modifier(
            link=self.link, key="test_key", multiplier=Decimal("2.0")
        )
        self.assertEqual(first.id, second.id)
        self.assertEqual(XpModifier.objects.filter(key="test_key").count(), 1)
        self.assertEqual(second.multiplier, Decimal("2.0"))

    def test_duration_computes_ends_at(self):
        now = timezone.now()
        mod = xpm.activate_link_modifier(
            link=self.link,
            key="test_key",
            multiplier=Decimal("1.5"),
            duration=timedelta(minutes=30),
            now=now,
        )
        self.assertEqual(mod.ends_at, now + timedelta(minutes=30))


class HandleOnlineLoginTests(TestCase):
    def setUp(self):
        self.user = user_factory(with_player=True)
        self.player = self.user.player
        self.character = Character.objects.create(given_name="Hero")

    def test_returns_none_without_active_link(self):
        self.assertIsNone(xpm.handle_online_login(self.player))
        self.assertFalse(XpModifier.objects.exists())

    def test_activates_indefinite_player_online_modifier(self):
        PlayerCharacterLink.objects.create(player=self.player, character=self.character)
        mod = xpm.handle_online_login(self.player)
        self.assertIsNotNone(mod)
        self.assertEqual(mod.key, xpm.PLAYER_ONLINE_KEY)
        self.assertEqual(mod.scope, XpModifier.Scope.CHARACTER)
        self.assertEqual(mod.character_id, self.character.id)
        self.assertEqual(mod.multiplier, Decimal(str(xpm.PLAYER_ONLINE_MULTIPLIER)))
        self.assertTrue(mod.is_active)
        self.assertIsNone(mod.ends_at)

    def test_relogin_cancels_pending_cooldown_end_task(self):
        link = PlayerCharacterLink.objects.create(
            player=self.player, character=self.character
        )
        mock_result = MagicMock(id="scheduled-task-id")
        with patch.object(xpm.end_xp_modifier, "apply_async", return_value=mock_result):
            xpm.schedule_online_end(link)

        mod = XpModifier.objects.get(key=xpm.PLAYER_ONLINE_KEY)
        self.assertEqual(mod.task_id, "scheduled-task-id")
        self.assertIsNotNone(mod.ends_at)

        with patch.object(xpm, "current_app") as mock_app:
            xpm.handle_online_login(self.player)

        mock_app.control.revoke.assert_called_once_with("scheduled-task-id")
        mod.refresh_from_db()
        self.assertIsNone(mod.task_id)
        self.assertIsNone(mod.ends_at)
        self.assertTrue(mod.is_active)


class ScheduleOnlineEndTests(TestCase):
    def setUp(self):
        self.player, self.character, self.link = _linked_player_and_character()

    def test_schedules_end_after_cooldown_instead_of_ending_immediately(self):
        mock_result = MagicMock(id="scheduled-task-id")
        with patch.object(
            xpm.end_xp_modifier, "apply_async", return_value=mock_result
        ) as mock_apply_async:
            xpm.schedule_online_end(self.link, cooldown_minutes=30)

        mod = XpModifier.objects.get(key=xpm.PLAYER_ONLINE_KEY)
        self.assertTrue(mod.is_active)
        self.assertIsNotNone(mod.ends_at)
        self.assertAlmostEqual(
            mod.ends_at,
            timezone.now() + timedelta(minutes=30),
            delta=timedelta(seconds=5),
        )
        self.assertEqual(mod.task_id, "scheduled-task-id")
        mock_apply_async.assert_called_once()
        self.assertEqual(
            mock_apply_async.call_args.kwargs["kwargs"], {"modifier_id": mod.id}
        )


class SetActivityActiveModifiersTests(TestCase):
    def setUp(self):
        self.player, self.character, self.link = _linked_player_and_character()

    def test_returns_empty_list_without_active_link(self):
        user = user_factory(with_player=True)
        self.assertEqual(
            xpm.set_activity_active_modifiers(user.player, is_active=True), []
        )
        self.assertFalse(XpModifier.objects.exists())

    def test_activating_creates_only_a_character_modifier(self):
        mods = xpm.set_activity_active_modifiers(self.player, is_active=True)
        self.assertEqual(len(mods), 1)

        character_mod = XpModifier.objects.get(
            scope=XpModifier.Scope.CHARACTER, key=xpm.ACTIVITY_ACTIVE_KEY
        )
        self.assertEqual(character_mod.character_id, self.character.id)
        self.assertEqual(
            character_mod.multiplier,
            Decimal(str(xpm.ACTIVITY_ACTIVE_CHARACTER_MULTIPLIER)),
        )
        self.assertTrue(character_mod.is_active)
        self.assertIsNone(character_mod.ends_at)

        # No player-scoped counterpart: it would be active exactly when the
        # player is earning AP, so it could never be off.
        self.assertFalse(
            XpModifier.objects.filter(scope=XpModifier.Scope.PLAYER).exists()
        )

    def test_deactivating_without_prior_activation_does_nothing(self):
        mods = xpm.set_activity_active_modifiers(self.player, is_active=False)
        self.assertEqual(mods, [])
        self.assertFalse(XpModifier.objects.exists())

    def test_deactivating_extends_ends_at_instead_of_ending_immediately(self):
        xpm.set_activity_active_modifiers(self.player, is_active=True)

        mock_result = MagicMock(id="grace-task-id")
        with patch.object(xpm.end_xp_modifier, "apply_async", return_value=mock_result):
            xpm.set_activity_active_modifiers(self.player, is_active=False)

        character_mod = XpModifier.objects.get(
            scope=XpModifier.Scope.CHARACTER, key=xpm.ACTIVITY_ACTIVE_KEY
        )

        self.assertTrue(character_mod.is_active)
        self.assertIsNotNone(character_mod.ends_at)
        self.assertAlmostEqual(
            character_mod.ends_at,
            timezone.now() + timedelta(minutes=xpm.ACTIVITY_ACTIVE_GRACE_MINUTES),
            delta=timedelta(seconds=5),
        )
        self.assertEqual(character_mod.task_id, "grace-task-id")

    def test_reactivating_within_grace_window_refreshes_and_cancels_pending_end(self):
        xpm.set_activity_active_modifiers(self.player, is_active=True)

        mock_result = MagicMock(id="grace-task-id")
        with patch.object(xpm.end_xp_modifier, "apply_async", return_value=mock_result):
            xpm.set_activity_active_modifiers(self.player, is_active=False)

        with patch.object(xpm, "current_app") as mock_app:
            xpm.set_activity_active_modifiers(self.player, is_active=True)

        self.assertEqual(mock_app.control.revoke.call_count, 1)

        character_mod = XpModifier.objects.get(
            scope=XpModifier.Scope.CHARACTER, key=xpm.ACTIVITY_ACTIVE_KEY
        )
        self.assertTrue(character_mod.is_active)
        self.assertIsNone(character_mod.ends_at)
        self.assertIsNone(character_mod.task_id)

        # Refreshed the existing row rather than creating a new one.
        self.assertEqual(
            XpModifier.objects.filter(key=xpm.ACTIVITY_ACTIVE_KEY).count(), 1
        )


class CharacterActivityRewardConsumptionTests(TestCase):
    """
    Confirms CharacterActivity.get_xp_reward_summary() (progression/models.py)
    still picks up the modifiers these functions create, now that they're
    live again - see issue #750.
    """

    def setUp(self):
        self.player, self.character, self.link = _linked_player_and_character()
        self.activity_definition = ActivityDefinition.objects.create(
            name="tending crops", kind=ActivityDefinition.Kind.WORK
        )

    def _make_activity(self, duration=600):
        now = timezone.now()
        return CharacterActivity.objects.create(
            character=self.character,
            activity_definition=self.activity_definition,
            started_at=now - timedelta(seconds=duration),
            duration=duration,
        )

    def test_no_active_modifiers_gives_unboosted_reward(self):
        activity = self._make_activity()
        summary = activity.get_xp_reward_summary()
        self.assertEqual(summary["boost_multiplier"], 1)

    def test_player_online_modifier_boosts_reward(self):
        xpm.handle_online_login(self.player)
        activity = self._make_activity()
        summary = activity.get_xp_reward_summary()
        self.assertEqual(summary["boost_multiplier"], xpm.PLAYER_ONLINE_MULTIPLIER)

    def test_activity_active_modifier_boosts_reward(self):
        xpm.set_activity_active_modifiers(self.player, is_active=True)
        activity = self._make_activity()
        summary = activity.get_xp_reward_summary()
        self.assertEqual(
            summary["boost_multiplier"], xpm.ACTIVITY_ACTIVE_CHARACTER_MULTIPLIER
        )

    def test_stacked_modifiers_multiply(self):
        xpm.handle_online_login(self.player)
        xpm.set_activity_active_modifiers(self.player, is_active=True)
        activity = self._make_activity()
        summary = activity.get_xp_reward_summary()
        expected = (
            xpm.PLAYER_ONLINE_MULTIPLIER * xpm.ACTIVITY_ACTIVE_CHARACTER_MULTIPLIER
        )
        self.assertEqual(summary["boost_multiplier"], expected)
