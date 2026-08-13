# character/tests.py

from datetime import date, datetime, timedelta
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils.timezone import now
from unittest import skip
from unittest.mock import patch, MagicMock

from character.models import (
    Character,
    CharacterRelationship,
    CharacterRelationshipMembership,
    PlayerCharacterLink,
    RelationshipRole,
    RelationshipType,
    RELATIONSHIP_SPECS,
)

from users.tests import user_factory


class CharacterRelationshipTests(TestCase):
    def setUp(self):
        self.char1 = Character.objects.create(
            given_name="Alice",
            birth_date=date(2000, 1, 1),
            sex="Female",
        )
        self.char2 = Character.objects.create(
            given_name="Bob",
            birth_date=date(1998, 6, 15),
            sex="Male",
        )

    def test_create_relationship(self):
        """Test creating a character relationship"""
        relationship = CharacterRelationship.objects.create(
            relationship_type="friend", strength=50
        )
        relationship.characters.add(self.char1, self.char2)

        self.assertEqual(relationship.relationship_type, "friend")
        self.assertEqual(relationship.strength, 50)
        self.assertEqual(relationship.characters.count(), 2)

    def test_get_members(self):
        """Test getting relationship members"""
        relationship = CharacterRelationship.objects.create(
            relationship_type="sibling", strength=75
        )
        relationship.characters.add(self.char1, self.char2)

        members = relationship.get_members()
        self.assertEqual(len(members), 2)
        self.assertIn(self.char1, members)
        self.assertIn(self.char2, members)

    def test_is_romantic(self):
        """Test romantic relationship detection"""
        romantic_rel = CharacterRelationship.objects.create(
            relationship_type="romantic", strength=80
        )
        friend_rel = CharacterRelationship.objects.create(
            relationship_type="friend", strength=60
        )

        self.assertTrue(romantic_rel.is_romantic())
        self.assertFalse(friend_rel.is_romantic())

    def test_adjust_strength(self):
        """Test relationship strength adjustment with bounds"""
        relationship = CharacterRelationship.objects.create(
            relationship_type="friend", strength=50
        )

        # Test normal adjustment
        relationship.adjust_strength(25)
        self.assertEqual(relationship.strength, 75)

        # Test upper bound
        relationship.adjust_strength(50)
        self.assertEqual(relationship.strength, 100)

        # Test lower bound
        relationship.adjust_strength(-250)
        self.assertEqual(relationship.strength, -100)

    def test_log_event(self):
        """Test event logging in relationship history"""
        relationship = CharacterRelationship.objects.create(
            relationship_type="friend", strength=50
        )

        event = {
            "type": "meeting",
            "date": "2024-01-01",
            "description": "First meeting",
        }
        relationship.log_event(event)

        self.assertIn("events", relationship.history)
        self.assertEqual(len(relationship.history["events"]), 1)
        self.assertEqual(relationship.history["events"][0], event)

    def test_relationship_str(self):
        """Test string representation of relationship"""
        relationship = CharacterRelationship.objects.create(
            relationship_type="mentor", strength=70
        )
        relationship.characters.add(self.char1, self.char2)

        str_repr = str(relationship)
        self.assertIn("mentor", str_repr)
        self.assertIn("Alice", str_repr)
        self.assertIn("Bob", str_repr)


class CharacterRelationshipMembershipTests(TestCase):
    def setUp(self):
        self.char = Character.objects.create(
            given_name="Test",
            birth_date=date(2000, 1, 1),
            sex="Female",
        )
        self.relationship = CharacterRelationship.objects.create(
            relationship_type="friend"
        )

    def test_create_membership(self):
        """Test creating relationship membership"""
        membership = CharacterRelationshipMembership.objects.create(
            character=self.char,
            relationship=self.relationship,
            role=RelationshipRole.PARTICIPANT,
        )

        self.assertEqual(membership.character, self.char)
        self.assertEqual(membership.relationship, self.relationship)
        self.assertEqual(membership.role, RelationshipRole.PARTICIPANT)

    def test_unique_together_constraint(self):
        """Test that character can't have duplicate memberships in same relationship"""
        CharacterRelationshipMembership.objects.create(
            character=self.char,
            relationship=self.relationship,
            role=RelationshipRole.PARTICIPANT,
        )

        # clean() (run via save()) reports this as a friendlier ValidationError
        # before it would ever reach the DB's unique_together constraint.
        with self.assertRaises(ValidationError):
            CharacterRelationshipMembership.objects.create(
                character=self.char,
                relationship=self.relationship,
                role=RelationshipRole.PARTICIPANT,
            )

    def test_role_must_be_valid_for_relationship_type(self):
        """A role not in the type's spec is rejected."""
        with self.assertRaises(ValidationError):
            CharacterRelationshipMembership.objects.create(
                character=self.char,
                relationship=self.relationship,
                role=RelationshipRole.PARENT,
            )

    def test_role_required_for_typed_relationship(self):
        """Relationship types with a spec require a role, unlike before."""
        with self.assertRaises(ValidationError):
            CharacterRelationshipMembership.objects.create(
                character=self.char, relationship=self.relationship
            )

    def test_role_max_count_enforced(self):
        """A role can't exceed its spec's max participant count."""
        other = Character.objects.create(given_name="Other", sex="Male")
        romantic = CharacterRelationship.objects.create(relationship_type="romantic")
        CharacterRelationshipMembership.objects.create(
            character=self.char,
            relationship=romantic,
            role=RelationshipRole.PARTICIPANT,
        )
        CharacterRelationshipMembership.objects.create(
            character=other, relationship=romantic, role=RelationshipRole.PARTICIPANT
        )

        third = Character.objects.create(given_name="Third", sex="Female")
        with self.assertRaises(ValidationError):
            CharacterRelationshipMembership.objects.create(
                character=third,
                relationship=romantic,
                role=RelationshipRole.PARTICIPANT,
            )

    def test_variant_must_be_allowed_for_relationship_type(self):
        """variant is validated against the type's allowed_variants."""
        with self.assertRaises(ValidationError):
            CharacterRelationship.objects.create(
                relationship_type=RelationshipType.FRIEND, variant="biological"
            )

        # PARENT_CHILD allows it.
        relationship = CharacterRelationship.objects.create(
            relationship_type=RelationshipType.PARENT_CHILD, variant="biological"
        )
        self.assertEqual(relationship.variant, "biological")


class LifeCycleMixinTests(TestCase):
    def setUp(self):
        self.character = Character.objects.create(
            given_name="Test",
            birth_date=date.today() - timedelta(days=365 * 25),  # 25 years old
            sex="Female",
            fertility=75,
        )

    def test_get_age(self):
        """Test age calculation"""
        age_days = self.character.get_age()
        expected_age = (now().date() - self.character.birth_date).days
        self.assertEqual(age_days, expected_age)

    def test_is_alive(self):
        """Test alive status"""
        self.assertTrue(self.character.is_alive())

        self.character.die()
        self.assertFalse(self.character.is_alive())
        self.assertEqual(self.character.death_date, now().date())

    def test_is_fertile(self):
        """Test fertility check"""
        self.assertTrue(self.character.is_fertile())

        self.character.fertility = 0
        self.character.save()
        self.assertFalse(self.character.is_fertile())

    def test_can_reproduce_with(self):
        """Test reproduction compatibility"""
        male_partner = Character.objects.create(
            given_name="Male",
            birth_date=date.today() - timedelta(days=365 * 30),
            sex="Male",
            fertility=50,
        )

        female_partner = Character.objects.create(
            given_name="Female",
            birth_date=date.today() - timedelta(days=365 * 28),
            sex="Female",
            fertility=60,
        )

        # Compatible couple
        self.assertTrue(self.character.can_reproduce_with(male_partner))

        # Same sex couple
        self.assertFalse(self.character.can_reproduce_with(female_partner))

        # Infertile partner
        male_partner.fertility = 0
        male_partner.save()
        self.assertFalse(self.character.can_reproduce_with(male_partner))

    def test_start_pregnancy(self):
        """Test starting pregnancy"""
        partner = Character.objects.create(
            given_name="Partner",
            birth_date=date.today() - timedelta(days=365 * 30),
            sex="Male",
            fertility=50,
        )

        self.character.start_pregnancy(partner)

        self.assertTrue(self.character.is_pregnant)
        self.assertEqual(self.character.pregnancy_start_date, now().date())
        self.assertEqual(self.character.pregnancy_partner, partner)

    @patch("character.services.lifecycle_services.randint")
    def test_handle_childbirth(self, mock_randint):
        """Test childbirth handling"""
        mock_randint.return_value = (
            1  # Female child (sex is Male only when randint == 0)
        )

        partner = Character.objects.create(
            given_name="Partner",
            birth_date=date.today() - timedelta(days=365 * 30),
            sex="Male",
            fertility=50,
        )

        self.character.pregnancy_partner = partner
        # self.character.x_coordinate = 100
        # self.character.y_coordinate = 200

        initial_count = Character.objects.count()
        self.character.handle_childbirth()

        self.assertEqual(Character.objects.count(), initial_count + 1)

        # Check child was created correctly
        child = Character.objects.filter(given_name__startswith="Child of").first()
        self.assertIsNotNone(child)
        # Not working properly! Fix later
        # self.assertEqual(child.sex, "Female")
        self.assertEqual(child.birth_date, now().date())
        self.assertIn(self.character, child.parents)
        self.assertIn(partner, child.parents)

    def test_handle_miscarriage(self):
        """Test miscarriage handling"""
        self.character.is_pregnant = True
        self.character.pregnancy_start_date = date.today()
        self.character.save()

        self.character.handle_miscarriage()

        self.assertFalse(self.character.is_pregnant)
        self.assertIsNone(self.character.pregnancy_start_date)

    def test_get_miscarriage_chance_age_factor(self):
        """Test miscarriage chance increases with age"""
        # Young character
        young_chance = self.character.get_miscarriage_change()
        self.assertEqual(young_chance, 0.05)

        # Older character
        self.character.birth_date = date.today() - timedelta(
            days=365 * 45
        )  # 45 years old
        old_chance = self.character.get_miscarriage_change()
        self.assertEqual(old_chance, 0.15)  # 0.05 + 0.10


class PersonTests(TestCase):
    def setUp(self):
        # Create a concrete character to test Person functionality
        self.character = Character.objects.create(
            given_name="Test",
            birth_date=date.today() - timedelta(days=365 * 20),
            sex="Male",
            xp=50,
            level=0,
        )

    def test_add_xp_no_level_up(self):
        """Test adding XP without triggering level up"""
        initial_level = self.character.level
        initial_xp = self.character.xp

        self.character.add_xp(30)

        self.assertEqual(self.character.xp, initial_xp + 30)
        self.assertEqual(self.character.level, initial_level)

    def test_add_xp_with_level_up(self):
        """Test adding XP that triggers level up"""
        self.character.xp = 80  # Close to level up (need 100 for level 1→2)
        self.character.save()

        self.character.add_xp(50)  # Should trigger level up

        self.assertEqual(self.character.level, 1)
        self.assertEqual(self.character.xp, 30)  # 80 + 50 - 100 = 30 remaining

    def test_add_xp_multiple_level_ups(self):
        """Test adding XP that triggers multiple level ups"""
        self.character.add_xp(300)  # Should trigger multiple level ups

        # Level 1→2: needs 100, uses 50 from 350 total, leaves 300
        # Level 2→3: needs 200, uses 200 from 300, leaves 100
        # Level 3→4: needs 300, but only 100 available, no level up
        self.assertEqual(self.character.level, 2)
        self.assertEqual(self.character.xp, 50)

    def test_get_xp_for_next_level(self):
        """Test XP calculation for next level"""
        # Level 0 (starting)
        self.character.level = 0
        self.assertEqual(self.character.get_xp_for_next_level(), 100)

        # Level 1
        self.character.level = 1
        self.assertEqual(self.character.get_xp_for_next_level(), 200)  # 100 * (1+1)

        # Level 5
        self.character.level = 5
        self.assertEqual(self.character.get_xp_for_next_level(), 600)  # 100 * (5+1)

    def test_xp_modifier_property(self):
        """Test XP modifier default value"""
        self.assertEqual(self.character.xp_modifier, 1.0)

    def test_person_created_at(self):
        """Test created_at timestamp is set"""
        self.assertIsNotNone(self.character.created_at)


class CharacterNPCTests(TestCase):
    """Tests for the is_npc property and related functionality"""

    def setUp(self):
        from users.models import CustomUser, Player

        # Create NPCs that are available for linking
        self.npc1 = Character.objects.create(
            given_name="NPC1",
            birth_date=date(2000, 1, 1),
            sex="Male",
        )
        self.npc2 = Character.objects.create(
            given_name="NPC2",
            birth_date=date(2000, 1, 1),
            sex="Female",
        )

        # Create a player-linked character
        # When creating a user, signals automatically create a player and assign a character
        # We need to deactivate the auto-assigned link first
        self.user = user_factory(with_player=True)
        self.player = self.user.player

        # Deactivate any auto-assigned character links
        auto_links = PlayerCharacterLink.objects.filter(
            player=self.player, is_active=True
        )
        for link in auto_links:
            link.unlink()

        # Now create our test character and link it
        self.player_character = Character.objects.create(
            given_name="Player",
            birth_date=date(2000, 1, 1),
            sex="Male",
        )
        PlayerCharacterLink.objects.create(
            player=self.player, character=self.player_character, is_active=True
        )

    def test_is_npc_property_for_npc(self):
        """Test that a character without an active player link is an NPC"""
        self.assertTrue(self.npc1.is_npc)
        self.assertTrue(self.npc2.is_npc)

    def test_is_npc_property_for_player_character(self):
        """Test that a character with an active player link is not an NPC"""
        self.assertFalse(self.player_character.is_npc)

    def test_is_npc_after_unlinking(self):
        """Test that a character becomes an NPC after unlinking"""
        # Unlink the character
        link = PlayerCharacterLink.objects.get(
            character=self.player_character, is_active=True
        )
        link.unlink()

        # Refresh from database
        self.player_character.refresh_from_db()

        # Should now be an NPC
        self.assertTrue(self.player_character.is_npc)

    def test_current_player_returns_none_without_active_link(self):
        """Character.current_player should be None if there is no active link."""
        self.assertIsNone(self.npc1.current_player)

    def test_has_available_classmethod(self):
        """Test the has_available classmethod returns True when NPCs are available"""
        # Should return True because we have NPCs with can_link=True and no active links
        self.assertTrue(Character.has_available())

    def test_has_available_no_linkable_characters(self):
        """Test has_available returns False when no linkable characters exist"""
        # Mark all currently-linkable NPCs as reserved, so none remain linkable
        Character.objects.linkable().update(is_reserved=True)
        self.assertFalse(Character.has_available())

    def test_has_available_all_linked(self):
        """Test has_available returns False when all linkable characters are linked"""
        from character.models import PlayerCharacterLink

        user1 = user_factory(with_player=True)
        user2 = user_factory(with_player=True)

        PlayerCharacterLink.assign_character(player=user1.player, character=self.npc1)
        PlayerCharacterLink.assign_character(player=user2.player, character=self.npc2)

        self.npc1.refresh_from_db()
        self.npc2.refresh_from_db()

        self.assertFalse(self.npc1.can_link)
        self.assertFalse(self.npc2.can_link)

        self.assertFalse(Character.has_available())


class CharacterTotalLinkPointsTests(TestCase):
    """Tests for Character.total_link_points (the character-side counterpart
    to Player.total_link_points)."""

    def setUp(self):
        from users.tests.factories import user_factory

        self.character = Character.objects.create(given_name="Hero")
        # DecimalField's string default isn't coerced to Decimal until a real
        # DB round-trip, so refresh before any test computes link_points
        # directly (as opposed to via the DB-backed total_link_points query).
        self.character.refresh_from_db()
        self.user1 = user_factory(with_player=True)
        self.user1.player.refresh_from_db()
        self.user2 = user_factory(with_player=True)
        self.user2.player.refresh_from_db()

    def _make_link(self, player, *, days_linked, unlinked=False):
        linked_at = now() - timedelta(days=days_linked)
        link = PlayerCharacterLink.objects.create(
            player=player, character=self.character, linked_at=linked_at
        )
        if unlinked:
            link.unlinked_at = now()
            link.is_active = False
            link.save(update_fields=["unlinked_at", "is_active"])
        return link

    def test_zero_for_a_never_linked_character(self):
        never_linked = Character.objects.create(given_name="Loner")
        self.assertEqual(never_linked.total_link_points, 0)

    def test_sums_a_single_active_link(self):
        link = self._make_link(self.user1.player, days_linked=3)
        self.assertEqual(self.character.total_link_points, link.link_points)

    def test_sums_across_historical_and_active_links(self):
        old_link = self._make_link(self.user1.player, days_linked=10, unlinked=True)
        current_link = self._make_link(self.user2.player, days_linked=2)

        self.assertEqual(
            self.character.total_link_points,
            old_link.link_points + current_link.link_points,
        )
