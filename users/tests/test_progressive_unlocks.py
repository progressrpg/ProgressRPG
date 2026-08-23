from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from core.models import GameSettings
from progression.models import PlayerActivity
from users.serializers import PlayerSerializer
from users.services import progressive_unlocks
from users.tests import user_factory


class ProgressiveUnlocksHelpersTest(TestCase):
    def setUp(self):
        GameSettings.objects.all().delete()
        self.settings = GameSettings.current()
        self.settings.progressive_unlocks_enabled_from = timezone.now() - timedelta(
            days=1
        )
        self.settings.save()

    def _new_signup(self):
        user = user_factory(with_player=True)
        return user.player

    def _legacy_player(self):
        user = user_factory(with_player=True)
        user.player.created_at = self.settings.progressive_unlocks_enabled_from - (
            timedelta(days=1)
        )
        user.player.save(update_fields=["created_at"])
        return user.player

    def _complete_activity(self, player):
        PlayerActivity.objects.create(player=player, is_complete=True)

    def test_legacy_player_is_not_a_new_signup(self):
        player = self._legacy_player()
        self.assertFalse(progressive_unlocks.is_new_signup(player))

    def test_fresh_player_is_a_new_signup(self):
        player = self._new_signup()
        self.assertTrue(progressive_unlocks.is_new_signup(player))

    def test_legacy_player_sees_everything_regardless_of_progress(self):
        player = self._legacy_player()
        for key in (
            progressive_unlocks.INFOBAR,
            progressive_unlocks.LIBRARY,
            progressive_unlocks.MAP,
        ):
            self.assertTrue(progressive_unlocks.unlock_visible(player, key))
            self.assertFalse(
                progressive_unlocks.new_signup_milestone_reached(player, key)
            )

    def test_new_signup_unlocks_infobar_after_first_activity(self):
        player = self._new_signup()
        self.assertFalse(
            progressive_unlocks.unlock_visible(player, progressive_unlocks.INFOBAR)
        )

        self._complete_activity(player)

        self.assertTrue(
            progressive_unlocks.unlock_visible(player, progressive_unlocks.INFOBAR)
        )
        self.assertTrue(
            progressive_unlocks.new_signup_milestone_reached(
                player, progressive_unlocks.INFOBAR
            )
        )

    def test_new_signup_unlocks_library_after_second_activity(self):
        player = self._new_signup()
        self._complete_activity(player)
        self.assertFalse(
            progressive_unlocks.unlock_visible(player, progressive_unlocks.LIBRARY)
        )

        self._complete_activity(player)

        self.assertTrue(
            progressive_unlocks.unlock_visible(player, progressive_unlocks.LIBRARY)
        )

    def test_new_signup_unlocks_map_at_level_4(self):
        player = self._new_signup()
        player.level = 3
        player.save(update_fields=["level"])
        self.assertFalse(
            progressive_unlocks.unlock_visible(player, progressive_unlocks.MAP)
        )

        player.level = 4
        player.save(update_fields=["level"])

        self.assertTrue(
            progressive_unlocks.unlock_visible(player, progressive_unlocks.MAP)
        )


class PlayerSerializerProgressiveUnlocksTest(TestCase):
    def setUp(self):
        GameSettings.objects.all().delete()
        self.settings = GameSettings.current()
        self.settings.progressive_unlocks_enabled_from = timezone.now() - timedelta(
            days=1
        )
        self.settings.save()

    def test_serializer_exposes_all_true_for_legacy_player(self):
        user = user_factory(with_player=True)
        user.player.created_at = self.settings.progressive_unlocks_enabled_from - (
            timedelta(days=1)
        )
        user.player.save(update_fields=["created_at"])

        data = PlayerSerializer(user.player).data

        self.assertEqual(
            data["progressive_unlocks"],
            {"infobar": True, "library": True, "map": True},
        )

    def test_serializer_gates_new_signup(self):
        user = user_factory(with_player=True)

        data = PlayerSerializer(user.player).data

        self.assertEqual(
            data["progressive_unlocks"],
            {"infobar": False, "library": False, "map": False},
        )

        PlayerActivity.objects.create(player=user.player, is_complete=True)

        data = PlayerSerializer(user.player).data
        self.assertTrue(data["progressive_unlocks"]["infobar"])
        self.assertFalse(data["progressive_unlocks"]["library"])


class UnseenTutorialStepGatingTest(TestCase):
    def setUp(self):
        GameSettings.objects.all().delete()
        self.settings = GameSettings.current()
        self.settings.progressive_unlocks_enabled_from = timezone.now() - timedelta(
            days=1
        )
        self.settings.save()

    def test_legacy_player_never_sees_gated_steps(self):
        user = user_factory(with_player=True)
        user.player.created_at = self.settings.progressive_unlocks_enabled_from - (
            timedelta(days=1)
        )
        user.player.save(update_fields=["created_at"])
        user.player.level = 10
        user.player.save(update_fields=["level"])
        for _ in range(3):
            PlayerActivity.objects.create(player=user.player, is_complete=True)

        data = PlayerSerializer(user.player).data
        gated_ids = set(self._gated_step_ids().values())
        self.assertTrue(gated_ids.isdisjoint(data["unseen_tutorial_step_ids"]))

    def test_new_signup_gains_step_id_exactly_at_milestone(self):
        user = user_factory(with_player=True)
        infobar_step_id = self._gated_step_ids()["infobar"]

        data = PlayerSerializer(user.player).data
        self.assertNotIn(infobar_step_id, data["unseen_tutorial_step_ids"])

        PlayerActivity.objects.create(player=user.player, is_complete=True)

        data = PlayerSerializer(user.player).data
        self.assertIn(infobar_step_id, data["unseen_tutorial_step_ids"])

    def _gated_step_ids(self):
        from users.models import TutorialStep

        return dict(
            TutorialStep.objects.exclude(unlock_key="").values_list("unlock_key", "id")
        )
