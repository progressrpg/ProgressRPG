"""
Tests for character.services.household_services - household_member_ages
(pure age/role planning, no DB) and create_household_relationships (turns
those roles into real MARRIAGE/PARENT_CHILD CharacterRelationship rows).
"""

from django.test import SimpleTestCase, TestCase

from character.models import Character, RelationshipType
from character.services import household_services
from character.services.household_services import (
    ADULT_AGE_RANGE,
    CHILD_AGE_RANGE,
    PARENT_CHILD_AGE_GAP_RANGE,
    create_household_relationships,
    household_member_ages,
)


class HouseholdMemberAgesTests(SimpleTestCase):
    def test_never_exceeds_remaining_budget(self):
        for budget in range(1, 30):
            household = household_member_ages(budget)
            self.assertLessEqual(len(household), budget)
            self.assertGreaterEqual(len(household), 1)

    def test_budget_of_one_is_a_single_adult(self):
        household = household_member_ages(1)
        self.assertEqual(household, [(household[0][0], "adult")])
        age, role = household[0]
        self.assertEqual(role, "adult")
        self.assertGreaterEqual(age, ADULT_AGE_RANGE[0])
        self.assertLessEqual(age, ADULT_AGE_RANGE[1])

    def test_ages_are_within_role_appropriate_ranges(self):
        for _ in range(200):
            for age, role in household_member_ages(6):
                if role == "child":
                    self.assertGreaterEqual(age, CHILD_AGE_RANGE[0])
                    self.assertLessEqual(age, CHILD_AGE_RANGE[1])
                else:
                    self.assertGreaterEqual(age, ADULT_AGE_RANGE[0])
                    self.assertLessEqual(age, ADULT_AGE_RANGE[1])

    def test_children_are_plausibly_younger_than_their_parents(self):
        min_gap, _max_gap = PARENT_CHILD_AGE_GAP_RANGE
        for _ in range(200):
            household = household_member_ages(6)
            parent_ages = [age for age, role in household if role == "parent"]
            child_ages = [age for age, role in household if role == "child"]
            if not parent_ages or not child_ages:
                continue
            youngest_parent = min(parent_ages)
            for child_age in child_ages:
                self.assertLessEqual(child_age, youngest_parent - min_gap)

    def test_running_total_across_many_households_hits_budget_exactly(self):
        # The pattern generate_characters.py actually uses: keep drawing
        # households until the centre's population budget is exhausted.
        for budget in (0, 1, 7, 23, 84):
            remaining = budget
            total = 0
            while remaining > 0:
                household = household_member_ages(remaining)
                remaining -= len(household)
                total += len(household)
            self.assertEqual(total, budget)


class CreateHouseholdRelationshipsTests(TestCase):
    def _make_character(self, name):
        return Character.objects.create(given_name=name, sex="Female")

    def test_two_parents_get_married(self):
        alice = self._make_character("Alice")
        bob = self._make_character("Bob")

        create_household_relationships([(alice, "parent"), (bob, "parent")])

        self.assertEqual(
            alice.relationships_of_type(RelationshipType.MARRIAGE).count(), 1
        )
        marriage = alice.relationships_of_type(RelationshipType.MARRIAGE).first()
        self.assertCountEqual(marriage.get_members(), [alice, bob])

    def test_parents_and_children_get_parent_child_relationships(self):
        alice = self._make_character("Alice")
        bob = self._make_character("Bob")
        kid = self._make_character("Kid")

        create_household_relationships(
            [(alice, "parent"), (bob, "parent"), (kid, "child")]
        )

        self.assertCountEqual(list(kid.parents), [alice, bob])
        self.assertIn(kid, list(alice.children))
        self.assertIn(kid, list(bob.children))

    def test_single_parent_household_has_no_marriage(self):
        alice = self._make_character("Alice")
        kid = self._make_character("Kid")

        create_household_relationships([(alice, "parent"), (kid, "child")])

        self.assertEqual(
            alice.relationships_of_type(RelationshipType.MARRIAGE).count(), 0
        )
        self.assertCountEqual(list(kid.parents), [alice])

    def test_roommates_get_no_relationships(self):
        alice = self._make_character("Alice")
        bob = self._make_character("Bob")

        create_household_relationships([(alice, "adult"), (bob, "adult")])

        self.assertEqual(
            alice.relationships_of_type(RelationshipType.MARRIAGE).count(), 0
        )
        self.assertEqual(list(alice.children), [])
        self.assertEqual(list(alice.parents), [])

    def test_single_adult_household_has_no_relationships(self):
        alice = self._make_character("Alice")

        create_household_relationships([(alice, "adult")])

        self.assertEqual(
            alice.relationships_of_type(RelationshipType.MARRIAGE).count(), 0
        )
