# character/tests/test_filters.py

from datetime import date
from django.test import TestCase

from character.models import Character, PlayerCharacterLink
from character.filters import CharacterFilter
from users.tests import user_factory


class CharacterFilterTests(TestCase):
    """Tests for CharacterFilter class"""

    def setUp(self):
        # Create NPCs that are available for linking
        self.npc1 = Character.objects.create(
            given_name="NPC1",
            birth_date=date(2000, 1, 1),
            sex="Male",
            level=5,
            xp=100,
        )
        self.npc2 = Character.objects.create(
            given_name="NPC2",
            birth_date=date(2000, 1, 1),
            sex="Female",
            level=10,
            xp=500,
        )

        # Create player characters
        # User creation auto-assigns characters, so we need to handle that
        self.user1 = user_factory(with_player=True)
        # Deactivate auto-assigned character
        auto_links = PlayerCharacterLink.objects.filter(
            player=self.user1.player, is_active=True
        )
        for link in auto_links:
            link.unlink()

        # Create and link our test character
        self.player_char1 = Character.objects.create(
            given_name="Player1",
            birth_date=date(2000, 1, 1),
            sex="Male",
            level=3,
            xp=75,
        )
        PlayerCharacterLink.objects.create(
            player=self.user1.player, character=self.player_char1, is_active=True
        )

        self.user2 = user_factory(with_player=True)
        # Deactivate auto-assigned character
        auto_links = PlayerCharacterLink.objects.filter(
            player=self.user2.player, is_active=True
        )
        for link in auto_links:
            link.unlink()

        # Create and link our test character
        self.player_char2 = Character.objects.create(
            given_name="Player2",
            birth_date=date(2000, 1, 1),
            sex="Female",
            level=7,
            xp=200,
        )
        PlayerCharacterLink.objects.create(
            player=self.user2.player, character=self.player_char2, is_active=True
        )

    def test_filter_can_link_true(self):
        """Test filtering for linkable characters"""
        filterset = CharacterFilter(
            data={"can_link": True}, queryset=Character.objects.all()
        )

        results = list(filterset.qs)
        self.assertIn(self.npc1, results)
        self.assertIn(self.npc2, results)
        self.assertNotIn(self.player_char1, results)
        self.assertNotIn(self.player_char2, results)

    def test_filter_level_range(self):
        """Test filtering by level range"""
        filterset = CharacterFilter(
            data={"level_min": 5, "level_max": 10}, queryset=Character.objects.all()
        )

        results = list(filterset.qs)
        self.assertIn(self.npc1, results)  # level 5
        self.assertIn(self.npc2, results)  # level 10
        self.assertIn(self.player_char2, results)  # level 7
        self.assertNotIn(self.player_char1, results)  # level 3

    def test_filter_xp_range(self):
        """Test filtering by XP range"""
        filterset = CharacterFilter(
            data={"xp_min": 100, "xp_max": 300}, queryset=Character.objects.all()
        )

        results = list(filterset.qs)
        self.assertIn(self.npc1, results)  # xp 100
        self.assertIn(self.player_char2, results)  # xp 200
        self.assertNotIn(self.player_char1, results)  # xp 75
        self.assertNotIn(self.npc2, results)  # xp 500

    def test_combined_filters(self):
        """Test using multiple filters together"""
        filterset = CharacterFilter(
            data={"can_link": True, "level_min": 5}, queryset=Character.objects.all()
        )

        results = list(filterset.qs)
        self.assertIn(self.npc1, results)  # can_link, level 5
        self.assertIn(self.npc2, results)  # can_link, level 10
        self.assertNotIn(self.player_char1, results)  # can_link=False
        self.assertNotIn(self.player_char2, results)  # can_link=False

    def test_filter_after_character_unlinked(self):
        """Test that can_link becomes True after unlinking"""
        # Unlink player_char1
        link = PlayerCharacterLink.objects.get(
            character=self.player_char1, is_active=True
        )
        link.unlink()

        # Refresh from database
        self.player_char1.refresh_from_db()

        # Filter for linkable characters
        filterset = CharacterFilter(
            data={"can_link": True}, queryset=Character.objects.all()
        )

        results = list(filterset.qs)
        # player_char1 should now be linkable after unlinking
        self.assertIn(self.player_char1, results)
        self.assertIn(self.npc1, results)
        self.assertIn(self.npc2, results)
        # player_char2 is still linked, so should not appear
        self.assertNotIn(self.player_char2, results)
