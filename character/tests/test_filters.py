# character/tests/test_filters.py

from datetime import date
from django.test import TestCase

from character.models import Character, PlayerCharacterLink
from character.filters import CharacterFilter
from users.models import CustomUser


class CharacterFilterTests(TestCase):
    """Tests for CharacterFilter class"""
    
    def setUp(self):
        # Create NPCs
        self.npc1 = Character.objects.create(
            first_name="NPC1",
            last_name="Character",
            birth_date=date(2000, 1, 1),
            sex="Male",
            can_link=True,
            level=5,
            xp=100,
        )
        self.npc2 = Character.objects.create(
            first_name="NPC2",
            last_name="Character",
            birth_date=date(2000, 1, 1),
            sex="Female",
            can_link=True,
            level=10,
            xp=500,
        )
        
        # Create player characters
        self.user1 = CustomUser.objects.create_user(
            email="user1@example.com",
            password="testpass123"
        )
        self.player_char1 = Character.objects.create(
            first_name="Player1",
            last_name="Character",
            birth_date=date(2000, 1, 1),
            sex="Male",
            can_link=False,
            level=3,
            xp=75,
        )
        PlayerCharacterLink.objects.create(
            player=self.user1.player,
            character=self.player_char1,
            is_active=True
        )
        
        self.user2 = CustomUser.objects.create_user(
            email="user2@example.com",
            password="testpass123"
        )
        self.player_char2 = Character.objects.create(
            first_name="Player2",
            last_name="Character",
            birth_date=date(2000, 1, 1),
            sex="Female",
            can_link=False,
            level=7,
            xp=200,
        )
        PlayerCharacterLink.objects.create(
            player=self.user2.player,
            character=self.player_char2,
            is_active=True
        )
    
    def test_filter_is_npc_true(self):
        """Test filtering for NPCs (is_npc=True)"""
        filterset = CharacterFilter(
            data={'is_npc': True},
            queryset=Character.objects.all()
        )
        
        # Should return only NPCs
        results = list(filterset.qs)
        self.assertIn(self.npc1, results)
        self.assertIn(self.npc2, results)
        self.assertNotIn(self.player_char1, results)
        self.assertNotIn(self.player_char2, results)
    
    def test_filter_is_npc_false(self):
        """Test filtering for player characters (is_npc=False)"""
        filterset = CharacterFilter(
            data={'is_npc': False},
            queryset=Character.objects.all()
        )
        
        # Should return only player characters
        results = list(filterset.qs)
        self.assertNotIn(self.npc1, results)
        self.assertNotIn(self.npc2, results)
        self.assertIn(self.player_char1, results)
        self.assertIn(self.player_char2, results)
    
    def test_filter_can_link_true(self):
        """Test filtering for linkable characters"""
        filterset = CharacterFilter(
            data={'can_link': True},
            queryset=Character.objects.all()
        )
        
        results = list(filterset.qs)
        self.assertIn(self.npc1, results)
        self.assertIn(self.npc2, results)
        self.assertNotIn(self.player_char1, results)
        self.assertNotIn(self.player_char2, results)
    
    def test_filter_level_range(self):
        """Test filtering by level range"""
        filterset = CharacterFilter(
            data={'level_min': 5, 'level_max': 10},
            queryset=Character.objects.all()
        )
        
        results = list(filterset.qs)
        self.assertIn(self.npc1, results)  # level 5
        self.assertIn(self.npc2, results)  # level 10
        self.assertIn(self.player_char2, results)  # level 7
        self.assertNotIn(self.player_char1, results)  # level 3
    
    def test_filter_xp_range(self):
        """Test filtering by XP range"""
        filterset = CharacterFilter(
            data={'xp_min': 100, 'xp_max': 300},
            queryset=Character.objects.all()
        )
        
        results = list(filterset.qs)
        self.assertIn(self.npc1, results)  # xp 100
        self.assertIn(self.player_char2, results)  # xp 200
        self.assertNotIn(self.player_char1, results)  # xp 75
        self.assertNotIn(self.npc2, results)  # xp 500
    
    def test_combined_filters(self):
        """Test using multiple filters together"""
        filterset = CharacterFilter(
            data={
                'is_npc': True,
                'can_link': True,
                'level_min': 5
            },
            queryset=Character.objects.all()
        )
        
        results = list(filterset.qs)
        self.assertIn(self.npc1, results)  # NPC, can_link, level 5
        self.assertIn(self.npc2, results)  # NPC, can_link, level 10
        self.assertNotIn(self.player_char1, results)  # Not NPC
        self.assertNotIn(self.player_char2, results)  # Not NPC
    
    def test_filter_after_character_unlinked(self):
        """Test that filter correctly identifies character as NPC after unlinking"""
        # Unlink player_char1
        link = PlayerCharacterLink.objects.get(
            character=self.player_char1,
            is_active=True
        )
        link.unlink()
        
        # Filter for NPCs
        filterset = CharacterFilter(
            data={'is_npc': True},
            queryset=Character.objects.all()
        )
        
        results = list(filterset.qs)
        # player_char1 should now appear as an NPC
        self.assertIn(self.player_char1, results)
        self.assertIn(self.npc1, results)
        self.assertIn(self.npc2, results)
        # player_char2 is still linked, so should not appear
        self.assertNotIn(self.player_char2, results)
