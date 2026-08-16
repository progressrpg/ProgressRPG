"""
Tests for character.signals - specifically that a CharacterRelationship is
cleaned up once every character in it has been deleted. Deleting a
Character cascades its CharacterRelationshipMembership rows (FK
on_delete=CASCADE), but CharacterRelationship itself has no FK for Django
to cascade from, so without this signal an orphaned, memberless
relationship row would survive forever (e.g. after
locations.generate_characters wipes and regenerates a village's cast).
"""

from django.test import TestCase

from character.models import (
    Character,
    CharacterRelationship,
    RelationshipRole,
    RelationshipType,
)
from character.services import relationship_services


class DeleteRelationshipWithNoMembersTests(TestCase):
    def _make_character(self, name):
        return Character.objects.create(given_name=name, sex="Female")

    def test_relationship_deleted_once_all_members_are_gone(self):
        alice = self._make_character("Alice")
        bob = self._make_character("Bob")
        relationship = relationship_services.relationship_create(
            RelationshipType.MARRIAGE,
            [
                (alice, RelationshipRole.SPOUSE),
                (bob, RelationshipRole.SPOUSE),
            ],
        )

        alice.delete()
        bob.delete()

        self.assertFalse(
            CharacterRelationship.objects.filter(id=relationship.id).exists()
        )

    def test_relationship_deleted_when_all_members_removed_in_one_bulk_delete(self):
        alice = self._make_character("Alice")
        bob = self._make_character("Bob")
        relationship = relationship_services.relationship_create(
            RelationshipType.MARRIAGE,
            [
                (alice, RelationshipRole.SPOUSE),
                (bob, RelationshipRole.SPOUSE),
            ],
        )

        Character.objects.filter(id__in=[alice.id, bob.id]).delete()

        self.assertFalse(
            CharacterRelationship.objects.filter(id=relationship.id).exists()
        )

    def test_relationship_survives_while_a_member_remains(self):
        alice = self._make_character("Alice")
        kid = self._make_character("Kid")
        relationship = relationship_services.relationship_create(
            RelationshipType.PARENT_CHILD,
            [
                (alice, RelationshipRole.PARENT),
                (kid, RelationshipRole.CHILD),
            ],
        )

        kid.delete()

        self.assertTrue(
            CharacterRelationship.objects.filter(id=relationship.id).exists()
        )
        self.assertEqual(relationship.get_members(), [alice])
