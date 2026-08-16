from core.models import GameSettings
from progression.models import PlayerActivity, PlayerSkill, player_total_skill_xp

from .base import BaseTestCase


class PlayerTotalSkillXpTests(BaseTestCase):
    """
    Mirrors progression.tests.test_activity_archive's coverage of
    character_total_skill_xp - see .claude/plans/progression-track-abstraction.md
    §9 for why player_total_skill_xp is a flat live aggregate, not a ledger.
    """

    def setUp(self):
        super().setUp()
        self.skill = PlayerSkill.objects.create(player=self.player, name="Coding")
        GameSettings.current()

    def test_sums_completed_skill_linked_activity_duration(self):
        PlayerActivity.objects.create(
            player=self.player,
            name="Write tests",
            skill=self.skill,
            duration=600,
            is_complete=True,
        )

        # An incomplete activity - excluded.
        PlayerActivity.objects.create(
            player=self.player,
            name="In progress",
            skill=self.skill,
            duration=999,
        )

        # A completed activity with no skill linked - excluded.
        PlayerActivity.objects.create(
            player=self.player,
            name="Unlinked",
            duration=999,
            is_complete=True,
        )

        # 600 seconds at the default 1.0 xp/sec rate.
        self.assertEqual(player_total_skill_xp(self.player), 600)

    def test_no_completed_skill_activity_returns_zero(self):
        self.assertEqual(player_total_skill_xp(self.player), 0)

    def test_query_count_stays_bounded(self):
        # One aggregate against PlayerActivity, one GameSettings lookup for
        # the XP rate - guards against this silently growing an N+1 later.
        with self.assertNumQueries(2):
            player_total_skill_xp(self.player)
