from datetime import timedelta
from decimal import Decimal

from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from character.models import Character
from gameplay.models import XpModifier
from progression import ap

from users.tests import user_factory


class ThresholdForLevelTests(SimpleTestCase):
    def test_level_zero(self):
        self.assertEqual(ap.threshold_for_level(0), 100)

    def test_scales_with_level(self):
        self.assertEqual(ap.threshold_for_level(1), 200)
        self.assertEqual(ap.threshold_for_level(4), 500)


class TotalApEarnedTests(SimpleTestCase):
    def test_level_zero_returns_xp_only(self):
        self.assertEqual(ap.total_ap_earned(0, 45), 45)

    def test_accumulates_cleared_thresholds(self):
        # level 1 means threshold_for_level(0) = 100 AP already cleared
        self.assertEqual(ap.total_ap_earned(1, 0), 100)

    def test_multiple_levels_cumulative(self):
        # thresholds for levels 0, 1, 2 = 100 + 200 + 300 = 600
        self.assertEqual(ap.total_ap_earned(3, 20), 620)


class ApplyXpTests(SimpleTestCase):
    def test_no_level_up(self):
        level, xp, levelups = ap.apply_xp(0, 0, 30)
        self.assertEqual((level, xp), (0, 30))
        self.assertEqual(levelups, [])

    def test_exact_level_up(self):
        level, xp, levelups = ap.apply_xp(0, 80, 50)
        self.assertEqual((level, xp), (1, 30))
        self.assertEqual(levelups, [{"old_level": 0, "new_level": 1}])

    def test_multiple_level_ups(self):
        level, xp, levelups = ap.apply_xp(0, 0, 300)
        self.assertEqual((level, xp), (2, 0))
        self.assertEqual(
            levelups,
            [
                {"old_level": 0, "new_level": 1},
                {"old_level": 1, "new_level": 2},
            ],
        )

    def test_remainder_carries_after_level_up(self):
        level, xp, levelups = ap.apply_xp(0, 50, 60)
        self.assertEqual((level, xp), (1, 10))
        self.assertEqual(levelups, [{"old_level": 0, "new_level": 1}])


class GetMultiplierTests(TestCase):
    def setUp(self):
        self.character = Character.objects.create(given_name="Test")
        self.now = timezone.now()

    def make_modifier(self, multiplier, **overrides):
        defaults = {
            "scope": XpModifier.Scope.CHARACTER,
            "character": self.character,
            "key": "test_modifier",
            "multiplier": multiplier,
            "starts_at": self.now - timedelta(hours=1),
            "is_active": True,
        }
        defaults.update(overrides)
        return XpModifier.objects.create(**defaults)

    def test_no_modifiers_returns_one(self):
        self.assertEqual(
            ap.get_multiplier(self.character, now=self.now), Decimal("1.0")
        )

    def test_single_active_modifier_applied(self):
        self.make_modifier(Decimal("1.5"))
        self.assertEqual(
            ap.get_multiplier(self.character, now=self.now), Decimal("1.5")
        )

    def test_multiple_active_modifiers_multiply(self):
        self.make_modifier(Decimal("1.5"), key="mod_a")
        self.make_modifier(Decimal("2"), key="mod_b")
        self.assertEqual(
            ap.get_multiplier(self.character, now=self.now), Decimal("3.0")
        )

    def test_inactive_modifier_excluded(self):
        self.make_modifier(Decimal("2"), is_active=False)
        self.assertEqual(
            ap.get_multiplier(self.character, now=self.now), Decimal("1.0")
        )

    def test_not_yet_started_modifier_excluded(self):
        self.make_modifier(Decimal("2"), starts_at=self.now + timedelta(hours=1))
        self.assertEqual(
            ap.get_multiplier(self.character, now=self.now), Decimal("1.0")
        )

    def test_expired_modifier_excluded(self):
        self.make_modifier(
            Decimal("2"),
            starts_at=self.now - timedelta(hours=2),
            ends_at=self.now - timedelta(hours=1),
        )
        self.assertEqual(
            ap.get_multiplier(self.character, now=self.now), Decimal("1.0")
        )

    def test_indefinite_modifier_included(self):
        self.make_modifier(Decimal("1.25"), ends_at=None)
        self.assertEqual(
            ap.get_multiplier(self.character, now=self.now), Decimal("1.25")
        )

    def test_defaults_to_current_time_when_now_not_passed(self):
        self.make_modifier(Decimal("2"))
        self.assertEqual(ap.get_multiplier(self.character), Decimal("2"))

    def test_works_for_player_scope_too(self):
        user = user_factory(with_player=True)
        player = user.player
        XpModifier.objects.create(
            scope=XpModifier.Scope.PLAYER,
            player=player,
            key="player_test_modifier",
            multiplier=Decimal("1.5"),
            starts_at=self.now - timedelta(hours=1),
            is_active=True,
        )
        self.assertEqual(ap.get_multiplier(player, now=self.now), Decimal("1.5"))


class GetProductivityTests(TestCase):
    def setUp(self):
        self.character = Character.objects.create(given_name="Test")
        self.now = timezone.now()

    def test_no_modifiers_returns_baseline(self):
        self.assertEqual(
            ap.get_productivity(self.character, now=self.now),
            ap.CHARACTER_BASELINE_PRODUCTIVITY,
        )

    def test_active_modifier_scales_baseline(self):
        XpModifier.objects.create(
            scope=XpModifier.Scope.CHARACTER,
            character=self.character,
            key="test_modifier",
            multiplier=Decimal("1.5"),
            starts_at=self.now - timedelta(hours=1),
            is_active=True,
        )
        self.assertEqual(
            ap.get_productivity(self.character, now=self.now),
            ap.CHARACTER_BASELINE_PRODUCTIVITY * Decimal("1.5"),
        )

    def test_inactive_modifier_excluded(self):
        XpModifier.objects.create(
            scope=XpModifier.Scope.CHARACTER,
            character=self.character,
            key="test_modifier",
            multiplier=Decimal("2"),
            starts_at=self.now - timedelta(hours=1),
            is_active=False,
        )
        self.assertEqual(
            ap.get_productivity(self.character, now=self.now),
            ap.CHARACTER_BASELINE_PRODUCTIVITY,
        )

    def test_character_get_productivity_matches_ap_function(self):
        XpModifier.objects.create(
            scope=XpModifier.Scope.CHARACTER,
            character=self.character,
            key="test_modifier",
            multiplier=Decimal("1.25"),
            starts_at=self.now - timedelta(hours=1),
            is_active=True,
        )
        self.assertEqual(
            self.character.get_productivity(now=self.now),
            ap.get_productivity(self.character, now=self.now),
        )
