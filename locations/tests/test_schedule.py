from datetime import datetime, time
from unittest.mock import patch

from django.contrib.gis.geos import Point
from django.test import TestCase
from django.utils import timezone

from locations.models import Node, Path, Building, PopulationCentre
from locations.services.schedule import sync_character_location, target_role_for
from locations.tasks import commute_tick
from character.models import Character, CharacterLocation


class ScheduleServiceTargetRoleTest(TestCase):
    def setUp(self):
        self.character = Character.objects.create(
            given_name="Scheduled", location=Point(0, 0, srid=3857)
        )

    def test_target_role_is_work_at_midday(self):
        noon = timezone.make_aware(datetime(2026, 1, 1, 12, 0, 0))
        self.assertEqual(
            target_role_for(self.character, now=noon), CharacterLocation.Role.WORK
        )

    def test_target_role_is_home_at_midnight(self):
        midnight = timezone.make_aware(datetime(2026, 1, 1, 0, 0, 0))
        self.assertEqual(
            target_role_for(self.character, now=midnight), CharacterLocation.Role.HOME
        )

    def test_target_role_respects_per_character_stagger_at_boundary(self):
        with patch(
            "locations.services.schedule._stagger_offset_seconds", return_value=0
        ):
            at_work_start = timezone.make_aware(datetime(2026, 1, 1, 8, 0, 0))
            just_before = timezone.make_aware(datetime(2026, 1, 1, 7, 59, 59))
            self.assertEqual(
                target_role_for(self.character, now=at_work_start),
                CharacterLocation.Role.WORK,
            )
            self.assertEqual(
                target_role_for(self.character, now=just_before),
                CharacterLocation.Role.HOME,
            )

        with patch(
            "locations.services.schedule._stagger_offset_seconds",
            return_value=600,
        ):
            # Boundary shifted 10 minutes later: 08:05 should still read HOME.
            shifted = timezone.make_aware(datetime(2026, 1, 1, 8, 5, 0))
            self.assertEqual(
                target_role_for(self.character, now=shifted),
                CharacterLocation.Role.HOME,
            )


class ScheduleServiceBuildingHoursTest(TestCase):
    def setUp(self):
        self.character = Character.objects.create(
            given_name="Worker", location=Point(0, 0, srid=3857)
        )

    def _assign_work(self, building):
        CharacterLocation.objects.create(
            character=self.character,
            location=building,
            role=CharacterLocation.Role.WORK,
        )

    def test_uses_building_override_hours(self):
        building = Building.objects.create(
            name="Late Mill",
            building_type="mill",
            location=Point(0, 0, srid=3857),
            open_time_override=time(20, 0),
            close_time_override=time(23, 0),
        )
        self._assign_work(building)

        with patch(
            "locations.services.schedule._stagger_offset_seconds", return_value=0
        ):
            during_override = timezone.make_aware(datetime(2026, 1, 1, 21, 0, 0))
            outside_default_hours = timezone.make_aware(datetime(2026, 1, 1, 8, 0, 0))
            self.assertEqual(
                target_role_for(self.character, now=during_override),
                CharacterLocation.Role.WORK,
            )
            self.assertEqual(
                target_role_for(self.character, now=outside_default_hours),
                CharacterLocation.Role.HOME,
            )

    def test_uses_building_type_default_hours(self):
        building = Building.objects.create(
            name="Bakery", building_type="bakery", location=Point(0, 0, srid=3857)
        )
        self._assign_work(building)

        with patch(
            "locations.services.schedule._stagger_offset_seconds", return_value=0
        ):
            during_default = timezone.make_aware(datetime(2026, 1, 1, 5, 0, 0))
            outside_default = timezone.make_aware(datetime(2026, 1, 1, 15, 0, 0))
            self.assertEqual(
                target_role_for(self.character, now=during_default),
                CharacterLocation.Role.WORK,
            )
            self.assertEqual(
                target_role_for(self.character, now=outside_default),
                CharacterLocation.Role.HOME,
            )

    def test_falls_back_to_constants_when_building_has_no_hours(self):
        building = Building.objects.create(
            name="Communal Hall",
            building_type="communal",
            location=Point(0, 0, srid=3857),
        )
        self._assign_work(building)

        with patch(
            "locations.services.schedule._stagger_offset_seconds", return_value=0
        ):
            noon = timezone.make_aware(datetime(2026, 1, 1, 12, 0, 0))
            midnight = timezone.make_aware(datetime(2026, 1, 1, 0, 0, 0))
            self.assertEqual(
                target_role_for(self.character, now=noon), CharacterLocation.Role.WORK
            )
            self.assertEqual(
                target_role_for(self.character, now=midnight),
                CharacterLocation.Role.HOME,
            )

    def test_falls_back_to_constants_when_no_work_location(self):
        with patch(
            "locations.services.schedule._stagger_offset_seconds", return_value=0
        ):
            noon = timezone.make_aware(datetime(2026, 1, 1, 12, 0, 0))
            self.assertEqual(
                target_role_for(self.character, now=noon), CharacterLocation.Role.WORK
            )

    def test_stagger_applied_to_building_resolved_hours(self):
        building = Building.objects.create(
            name="Market", building_type="market", location=Point(0, 0, srid=3857)
        )
        self._assign_work(building)

        # Market default hours are 08:00-16:00; shift the boundary 10 minutes
        # later via stagger and confirm it's respected.
        with patch(
            "locations.services.schedule._stagger_offset_seconds",
            return_value=600,
        ):
            shifted = timezone.make_aware(datetime(2026, 1, 1, 8, 5, 0))
            self.assertEqual(
                target_role_for(self.character, now=shifted),
                CharacterLocation.Role.HOME,
            )


class SyncCharacterLocationTest(TestCase):
    def setUp(self):
        self.start_node = Node.objects.create(
            name="Start", location=Point(0, 0, srid=3857), kind=Node.Kind.OUTSIDE
        )
        self.home_building = Building.objects.create(
            name="Home", building_type="residential", location=Point(0, 0, srid=3857)
        )
        self.work_building = Building.objects.create(
            name="Work", building_type="communal", location=Point(20, 0, srid=3857)
        )
        self.home_node = Node.objects.create(
            name="HomeEntrance",
            location=Point(0, 0, srid=3857),
            kind=Node.Kind.BUILDING_ENTRANCE,
            building=self.home_building,
        )
        self.work_node = Node.objects.create(
            name="WorkEntrance",
            location=Point(20, 0, srid=3857),
            kind=Node.Kind.BUILDING_ENTRANCE,
            building=self.work_building,
        )
        Path.objects.create(from_node=self.start_node, to_node=self.home_node)
        Path.objects.create(from_node=self.start_node, to_node=self.work_node)
        Path.objects.create(from_node=self.home_node, to_node=self.work_node)

        self.character = Character.objects.create(
            given_name="Commuter",
            location=Point(0, 0, srid=3857),
            current_node=self.start_node,
        )
        CharacterLocation.objects.create(
            character=self.character,
            location=self.home_building,
            role=CharacterLocation.Role.HOME,
        )
        CharacterLocation.objects.create(
            character=self.character,
            location=self.work_building,
            role=CharacterLocation.Role.WORK,
        )

    def test_moves_toward_work_during_day(self):
        with patch(
            "locations.services.schedule.target_role_for",
            return_value=CharacterLocation.Role.WORK,
        ), patch("locations.tasks.move_characters_tick.apply_async"):
            sync_character_location(self.character)

        self.character.refresh_from_db()
        self.assertTrue(self.character.is_moving)
        self.assertEqual(self.character.target_node, self.work_node)

    def test_moves_toward_home_at_night(self):
        with patch(
            "locations.services.schedule.target_role_for",
            return_value=CharacterLocation.Role.HOME,
        ), patch("locations.tasks.move_characters_tick.apply_async"):
            sync_character_location(self.character)

        self.character.refresh_from_db()
        self.assertTrue(self.character.is_moving)
        self.assertEqual(self.character.target_node, self.home_node)

    def test_noop_when_already_at_target(self):
        self.character.current_node = self.home_node
        self.character.save(update_fields=["current_node"])

        with patch(
            "locations.services.schedule.target_role_for",
            return_value=CharacterLocation.Role.HOME,
        ):
            sync_character_location(self.character)

        self.character.refresh_from_db()
        self.assertFalse(self.character.is_moving)
        self.assertIsNone(self.character.target_node)

    def test_noop_when_already_heading_there(self):
        # is_moving False but target_node already set to the destination -
        # e.g. leftover from a cancelled journey. Should not re-trigger.
        self.character.target_node = self.work_node
        self.character.save(update_fields=["target_node"])

        with patch.object(
            self.character, "set_destination"
        ) as mock_set_destination, patch(
            "locations.services.schedule.target_role_for",
            return_value=CharacterLocation.Role.WORK,
        ):
            sync_character_location(self.character)

        mock_set_destination.assert_not_called()

    def test_noop_when_is_moving(self):
        self.character.is_moving = True
        self.character.save(update_fields=["is_moving"])

        with patch("locations.services.schedule.target_role_for") as mock_target_role:
            sync_character_location(self.character)

        mock_target_role.assert_not_called()

    def test_noop_when_no_matching_character_location(self):
        CharacterLocation.objects.filter(
            character=self.character, role=CharacterLocation.Role.WORK
        ).delete()

        with patch(
            "locations.services.schedule.target_role_for",
            return_value=CharacterLocation.Role.WORK,
        ):
            sync_character_location(self.character)

        self.character.refresh_from_db()
        self.assertFalse(self.character.is_moving)

    def test_catches_value_error_from_set_destination(self):
        with patch(
            "locations.services.schedule.target_role_for",
            return_value=CharacterLocation.Role.WORK,
        ), patch.object(
            self.character, "set_destination", side_effect=ValueError("no path")
        ):
            sync_character_location(self.character)  # should not raise

        self.character.refresh_from_db()
        self.assertFalse(self.character.is_moving)


class CommuteTickTaskTest(TestCase):
    def setUp(self):
        self.centre = PopulationCentre.objects.create(
            name="Commute Village", location=Point(0, 0, srid=3857)
        )
        self.idle_character = Character.objects.create(
            given_name="Idle",
            location=Point(0, 0, srid=3857),
            population_centre=self.centre,
            is_moving=False,
        )
        self.moving_character = Character.objects.create(
            given_name="Moving",
            location=Point(0, 0, srid=3857),
            population_centre=self.centre,
            is_moving=True,
        )
        self.orphan_character = Character.objects.create(
            given_name="Orphan",
            location=Point(0, 0, srid=3857),
            is_moving=False,
        )

    def test_commute_tick_only_syncs_idle_village_assigned_characters(self):
        with patch("locations.services.schedule.sync_character_location") as mock_sync:
            commute_tick()

        synced_ids = {call.args[0].id for call in mock_sync.call_args_list}
        self.assertEqual(synced_ids, {self.idle_character.id})
