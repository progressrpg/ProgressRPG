"""
Tests for relationship_services.relationship_get_household_members and
household_relationship_label - the "Thomas — husband" style summary used by
the map's character detail card (see locations.serializers.
CharacterDetailSerializer).
"""

from django.test import SimpleTestCase, TestCase

from character.models import Character, RelationshipRole, RelationshipType
from character.services import relationship_services


class RelationshipGetHouseholdMembersTests(TestCase):
    def _make_character(self, name, sex="Female"):
        return Character.objects.create(given_name=name, sex=sex)

    def test_marriage_partner_is_included(self):
        alice = self._make_character("Alice", sex="Female")
        bob = self._make_character("Bob", sex="Male")
        relationship_services.relationship_create(
            RelationshipType.MARRIAGE,
            [
                (alice, RelationshipRole.SPOUSE),
                (bob, RelationshipRole.SPOUSE),
            ],
        )

        members = relationship_services.relationship_get_household_members(alice)

        self.assertEqual(len(members), 1)
        self.assertEqual(members[0]["character"], bob)
        self.assertEqual(members[0]["relationship_type"], RelationshipType.MARRIAGE)
        self.assertEqual(members[0]["other_role"], RelationshipRole.SPOUSE)

    def test_parent_and_child_see_each_other_with_the_right_role(self):
        alice = self._make_character("Alice")
        kid = self._make_character("Kid")
        relationship_services.relationship_create(
            RelationshipType.PARENT_CHILD,
            [
                (alice, RelationshipRole.PARENT),
                (kid, RelationshipRole.CHILD),
            ],
        )

        alice_members = relationship_services.relationship_get_household_members(alice)
        kid_members = relationship_services.relationship_get_household_members(kid)

        self.assertEqual(alice_members[0]["character"], kid)
        self.assertEqual(alice_members[0]["other_role"], RelationshipRole.CHILD)
        self.assertEqual(kid_members[0]["character"], alice)
        self.assertEqual(kid_members[0]["other_role"], RelationshipRole.PARENT)

    def test_only_marriage_and_parent_child_types_are_included(self):
        alice = self._make_character("Alice")
        rival = self._make_character("Rival")
        relationship_services.relationship_create(
            RelationshipType.RIVAL,
            [
                (alice, RelationshipRole.PARTICIPANT),
                (rival, RelationshipRole.PARTICIPANT),
            ],
        )

        self.assertEqual(
            relationship_services.relationship_get_household_members(alice), []
        )

    def test_character_with_no_relationships_returns_empty_list(self):
        alice = self._make_character("Alice")

        self.assertEqual(
            relationship_services.relationship_get_household_members(alice), []
        )


class HouseholdRelationshipLabelTests(SimpleTestCase):
    def test_marriage_labels_by_sex(self):
        self.assertEqual(
            relationship_services.household_relationship_label(
                RelationshipType.MARRIAGE, RelationshipRole.SPOUSE, "Male"
            ),
            "husband",
        )
        self.assertEqual(
            relationship_services.household_relationship_label(
                RelationshipType.MARRIAGE, RelationshipRole.SPOUSE, "Female"
            ),
            "wife",
        )
        self.assertEqual(
            relationship_services.household_relationship_label(
                RelationshipType.MARRIAGE, RelationshipRole.SPOUSE, "Other"
            ),
            "spouse",
        )

    def test_parent_child_labels_depend_on_the_others_role(self):
        self.assertEqual(
            relationship_services.household_relationship_label(
                RelationshipType.PARENT_CHILD, RelationshipRole.PARENT, "Female"
            ),
            "mother",
        )
        self.assertEqual(
            relationship_services.household_relationship_label(
                RelationshipType.PARENT_CHILD, RelationshipRole.CHILD, "Male"
            ),
            "son",
        )
        self.assertEqual(
            relationship_services.household_relationship_label(
                RelationshipType.PARENT_CHILD, RelationshipRole.CHILD, "Female"
            ),
            "daughter",
        )
