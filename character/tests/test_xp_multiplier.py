# character/tests/test_xp_multiplier.py

from datetime import date, timedelta
from django.test import TestCase
from django.utils import timezone
from unittest.mock import patch

from character.models import Character, PlayerCharacterLink
from progression.models import CharacterActivity
from character.models.behaviour import Behaviour
from users.models import CustomUser, Player


class XPMultiplierSystemTests(TestCase):
    """Test suite for the symbiotic XP multiplier system."""

    def setUp(self):
        """Set up test data for XP multiplier tests."""
        # Create a user
        self.user = CustomUser.objects.create_user(
            email="testuser@example.com",
            password="testpass123"
        )
        
        # Create a player
        self.player = Player.objects.create(
            user=self.user,
            name="Test Player",
            is_online=False
        )
        
        # Create a character
        self.character = Character.objects.create(
            first_name="Test",
            last_name="Character",
            birth_date=date.today() - timedelta(days=365 * 25),
            sex="Female",
            can_link=True
        )
        
        # Create behaviour for the character
        self.behaviour = Behaviour.objects.create(character=self.character)
        
        # Link player to character
        self.link = PlayerCharacterLink.assign_character(self.player, self.character)

    def test_player_is_online_property(self):
        """Test that player_is_online property works correctly."""
        # Player is offline by default
        self.assertFalse(self.link.player_is_online)
        
        # Set player online
        self.player.is_online = True
        self.player.save()
        self.link.refresh_from_db()
        
        self.assertTrue(self.link.player_is_online)

    def test_xp_multiplier_offline(self):
        """Test that XP multiplier is 1.0 when player is offline."""
        self.player.is_online = False
        self.player.save()
        self.link.refresh_from_db()
        
        self.assertEqual(self.link.xp_multiplier, 1.0)
        self.assertEqual(self.character.xp_multiplier, 1.0)

    def test_xp_multiplier_online(self):
        """Test that XP multiplier is 2.0 when player is online."""
        self.player.is_online = True
        self.player.save()
        self.link.refresh_from_db()
        
        self.assertEqual(self.link.xp_multiplier, 2.0)
        self.assertEqual(self.character.xp_multiplier, 2.0)

    def test_get_link_for_character(self):
        """Test getting active link for a character."""
        link = PlayerCharacterLink.get_link_for_character(self.character)
        self.assertIsNotNone(link)
        self.assertEqual(link.character, self.character)
        self.assertEqual(link.player, self.player)

    def test_get_link_for_player(self):
        """Test getting active link for a player."""
        link = PlayerCharacterLink.get_link_for_player(self.player)
        self.assertIsNotNone(link)
        self.assertEqual(link.player, self.player)
        self.assertEqual(link.character, self.character)

    def test_character_activity_captures_multiplier_offline(self):
        """Test that CharacterActivity captures multiplier when created offline."""
        self.player.is_online = False
        self.player.save()
        
        now = timezone.now()
        activity = CharacterActivity.objects.create(
            character=self.character,
            kind="work",
            name="Working",
            scheduled_start=now,
            scheduled_end=now + timedelta(hours=2),
            started_at=now,
            is_complete=False
        )
        
        self.assertEqual(activity.xp_multiplier_applied, 1.0)

    def test_character_activity_captures_multiplier_online(self):
        """Test that CharacterActivity captures multiplier when created online."""
        self.player.is_online = True
        self.player.save()
        
        now = timezone.now()
        activity = CharacterActivity.objects.create(
            character=self.character,
            kind="work",
            name="Working",
            scheduled_start=now,
            scheduled_end=now + timedelta(hours=2),
            started_at=now,
            is_complete=False
        )
        
        self.assertEqual(activity.xp_multiplier_applied, 2.0)

    def test_activity_xp_calculation_uses_stored_multiplier(self):
        """Test that XP calculation uses stored multiplier, not current state."""
        # Create activity while offline (1.0x)
        self.player.is_online = False
        self.player.save()
        
        now = timezone.now()
        activity = CharacterActivity.objects.create(
            character=self.character,
            kind="work",
            name="Working",
            scheduled_start=now,
            scheduled_end=now + timedelta(hours=2),
            started_at=now,
            duration=7200,  # 2 hours in seconds
            is_complete=False
        )
        
        # Player comes online - but activity should still use 1.0x
        self.player.is_online = True
        self.player.save()
        
        # Calculate XP - should use stored 1.0x multiplier
        xp = activity.calculate_xp_reward()
        expected_xp = (7200 // 60) * 1.0 * 1.0  # 120 XP
        self.assertEqual(xp, int(expected_xp))
        self.assertEqual(activity.xp_multiplier_applied, 1.0)

    def test_activity_xp_calculation_with_online_multiplier(self):
        """Test XP calculation with online multiplier."""
        # Create activity while online (2.0x)
        self.player.is_online = True
        self.player.save()
        
        now = timezone.now()
        activity = CharacterActivity.objects.create(
            character=self.character,
            kind="work",
            name="Working",
            scheduled_start=now,
            scheduled_end=now + timedelta(hours=2),
            started_at=now,
            duration=7200,  # 2 hours in seconds
            is_complete=False
        )
        
        # Calculate XP - should use 2.0x multiplier
        xp = activity.calculate_xp_reward()
        expected_xp = (7200 // 60) * 1.0 * 2.0  # 240 XP
        self.assertEqual(xp, int(expected_xp))
        self.assertEqual(activity.xp_multiplier_applied, 2.0)

    def test_activity_xp_calculation_with_rest_activity(self):
        """Test XP calculation for rest activity (0.25x activity multiplier)."""
        self.player.is_online = True
        self.player.save()
        
        now = timezone.now()
        activity = CharacterActivity.objects.create(
            character=self.character,
            kind="rest",
            name="Resting",
            scheduled_start=now,
            scheduled_end=now + timedelta(hours=2),
            started_at=now,
            duration=7200,  # 2 hours in seconds
            is_complete=False
        )
        
        # Calculate XP - should use 0.25x activity multiplier * 2.0x player multiplier
        xp = activity.calculate_xp_reward()
        expected_xp = (7200 // 60) * 0.25 * 2.0  # 60 XP
        self.assertEqual(xp, int(expected_xp))

    def test_on_player_state_change_interrupts_activity(self):
        """Test that on_player_state_change interrupts current activity."""
        # Generate a day of activities
        today = timezone.now().date()
        self.behaviour.generate_day(today)
        
        # Sync to get current activity
        now = timezone.now()
        current = self.behaviour.sync_to_now(now)
        
        # Skip if no current activity or it's sleep
        if not current or current.kind == 'sleep':
            self.skipTest("No suitable activity to test with")
        
        original_end = current.scheduled_end
        
        # Change player state
        new_activity = self.character.on_player_state_change(now)
        
        if new_activity:
            # Old activity should be complete
            current.refresh_from_db()
            self.assertTrue(current.is_complete)
            self.assertEqual(current.completed_at, now)
            
            # New activity should be scheduled for remaining time
            self.assertEqual(new_activity.scheduled_end, original_end)
            self.assertEqual(new_activity.scheduled_start, now)
            self.assertFalse(new_activity.is_complete)

    def test_on_player_state_change_does_not_interrupt_sleep(self):
        """Test that sleep activities are not interrupted."""
        now = timezone.now()
        
        # Create a sleep activity
        sleep_activity = CharacterActivity.objects.create(
            character=self.character,
            kind="sleep",
            name="Sleep",
            scheduled_start=now - timedelta(hours=1),
            scheduled_end=now + timedelta(hours=6),
            started_at=now - timedelta(hours=1),
            is_complete=False
        )
        
        # Try to change player state
        result = self.character.on_player_state_change(now)
        
        # Should return the sleep activity unchanged
        self.assertEqual(result, sleep_activity)
        sleep_activity.refresh_from_db()
        self.assertFalse(sleep_activity.is_complete)

    def test_on_player_state_change_does_not_interrupt_short_activities(self):
        """Test that activities with less than 5 minutes remaining are not interrupted."""
        now = timezone.now()
        
        # Create an activity with 4 minutes remaining
        activity = CharacterActivity.objects.create(
            character=self.character,
            kind="work",
            name="Working",
            scheduled_start=now - timedelta(hours=1),
            scheduled_end=now + timedelta(minutes=4),
            started_at=now - timedelta(hours=1),
            is_complete=False
        )
        
        # Try to change player state
        result = self.character.on_player_state_change(now)
        
        # Should return the activity unchanged
        self.assertEqual(result, activity)
        activity.refresh_from_db()
        self.assertFalse(activity.is_complete)

    def test_on_player_state_change_captures_new_multiplier(self):
        """Test that new activity after state change captures new multiplier."""
        # Start offline
        self.player.is_online = False
        self.player.save()
        
        now = timezone.now()
        
        # Create an activity
        activity = CharacterActivity.objects.create(
            character=self.character,
            kind="work",
            name="Working",
            scheduled_start=now - timedelta(hours=1),
            scheduled_end=now + timedelta(hours=2),
            started_at=now - timedelta(hours=1),
            is_complete=False
        )
        
        # Verify it has 1.0x multiplier
        self.assertEqual(activity.xp_multiplier_applied, 1.0)
        
        # Player comes online
        self.player.is_online = True
        self.player.save()
        
        # Trigger state change
        new_activity = self.character.on_player_state_change(now)
        
        if new_activity:
            # New activity should have 2.0x multiplier
            self.assertEqual(new_activity.xp_multiplier_applied, 2.0)
            
            # Old activity should still have 1.0x multiplier
            activity.refresh_from_db()
            self.assertEqual(activity.xp_multiplier_applied, 1.0)

    def test_character_without_link_has_default_multiplier(self):
        """Test that character without active link has 1.0x multiplier."""
        # Create a character without a link
        unlinked_char = Character.objects.create(
            first_name="Unlinked",
            last_name="Character",
            birth_date=date.today() - timedelta(days=365 * 30),
            sex="Male"
        )
        
        self.assertEqual(unlinked_char.xp_multiplier, 1.0)
        self.assertFalse(unlinked_char.player_is_online)

    def test_completed_activity_not_interrupted(self):
        """Test that completed activities are not interrupted."""
        now = timezone.now()
        
        # Create a completed activity
        activity = CharacterActivity.objects.create(
            character=self.character,
            kind="work",
            name="Working",
            scheduled_start=now - timedelta(hours=2),
            scheduled_end=now - timedelta(hours=1),
            started_at=now - timedelta(hours=2),
            completed_at=now - timedelta(hours=1),
            is_complete=True,
            duration=3600
        )
        
        # Try to change player state
        result = self.character.on_player_state_change(now)
        
        # Should return None since there's no active activity
        self.assertIsNone(result)
