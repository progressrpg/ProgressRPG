from django.contrib.gis.geos import Point, Polygon
from django.test import TestCase
from django.utils import timezone

from character.models import Character, CharacterLocation
from economy.models import FieldCrop, GoodsStock
from progression.models import ActivityDefinition, CharacterActivity

from users.tests import user_factory

from ..models import Building, LandArea, PopulationCentre, Subzone
from ..serializers import (
    BuildingFeatureSerializer,
    CharacterDetailSerializer,
    CharacterPointFeatureSerializer,
    PopulationCentreLabelFeatureSerializer,
    SubzoneFeatureSerializer,
)
from locations.constants import PROJECT_SRID
from ..services import population_estimation

SQUARE = Polygon(
    ((0, 0), (0, 10), (10, 10), (10, 0), (0, 0)),
    srid=PROJECT_SRID,
)


class BuildingFeatureSerializerTest(TestCase):
    def setUp(self):
        self.building = Building.objects.create(
            name="Bakery",
            building_type="bakery",
            footprint=SQUARE,
        )

    def properties(self):
        building = Building.objects.prefetch_related(
            "character_locations", "goods_stocks"
        ).get(pk=self.building.pk)
        return BuildingFeatureSerializer(building).data["properties"]

    def test_zero_workers_and_no_stock(self):
        props = self.properties()
        self.assertEqual(props["workers"], 0)
        self.assertEqual(props["residents"], 0)
        self.assertEqual(props["goods"], [])

    def test_workers_counts_only_primary_work_locations(self):
        worker = Character.objects.create(given_name="Worker")
        CharacterLocation.objects.create(
            character=worker,
            location=self.building,
            role=CharacterLocation.Role.WORK,
            is_primary=True,
        )
        not_primary = Character.objects.create(given_name="Substitute")
        CharacterLocation.objects.create(
            character=not_primary,
            location=self.building,
            role=CharacterLocation.Role.WORK,
            is_primary=False,
        )
        home_only = Character.objects.create(given_name="Resident")
        CharacterLocation.objects.create(
            character=home_only,
            location=self.building,
            role=CharacterLocation.Role.HOME,
            is_primary=True,
        )

        props = self.properties()
        self.assertEqual(props["workers"], 1)
        self.assertEqual(props["residents"], 1)

    def test_residential_capacity_is_zero_for_a_non_residential_building(self):
        self.assertEqual(self.properties()["residential_capacity"], 0)

    def test_residential_capacity_matches_the_service_for_a_residential_building(self):
        house = Building.objects.create(
            name="House", building_type="residential", footprint=SQUARE
        )
        house = Building.objects.prefetch_related(
            "character_locations", "goods_stocks"
        ).get(pk=house.pk)
        props = BuildingFeatureSerializer(house).data["properties"]
        self.assertEqual(
            props["residential_capacity"],
            population_estimation.residential_capacity(house),
        )
        self.assertGreater(props["residential_capacity"], 0)

    def test_goods_only_include_positive_stock_using_format_quantity(self):
        GoodsStock.objects.create(
            building=self.building, good_type="flour", quantity=21000
        )
        GoodsStock.objects.create(
            building=self.building, good_type="bread", quantity=18000
        )
        GoodsStock.objects.create(building=self.building, good_type="wheat", quantity=0)

        goods = {g["good_type"]: g["display"] for g in self.properties()["goods"]}
        self.assertEqual(goods, {"flour": "2 sacks", "bread": "18.0 loaves"})


class CharacterPointFeatureSerializerTest(TestCase):
    def setUp(self):
        self.home = Building.objects.create(
            name="Rose Cottage", building_type="residential"
        )
        self.work = Building.objects.create(
            name="Village Bakery", building_type="bakery"
        )
        self.character = Character.objects.create(
            given_name="Alice", location=Point(0, 0, srid=PROJECT_SRID)
        )

    def properties(self):
        character = (
            Character.objects.select_related("needs")
            .prefetch_related("locations__location")
            .get(pk=self.character.pk)
        )
        return CharacterPointFeatureSerializer(character).data["properties"]

    def test_no_home_or_work_assigned(self):
        props = self.properties()
        self.assertIsNone(props["home_type"])
        self.assertIsNone(props["work_type"])
        self.assertIsNone(props["home_id"])

    def test_home_id_matches_the_primary_home_building(self):
        CharacterLocation.objects.create(
            character=self.character,
            location=self.home,
            role=CharacterLocation.Role.HOME,
            is_primary=True,
        )

        self.assertEqual(self.properties()["home_id"], self.home.id)

    def test_home_and_work_type_from_primary_locations_only(self):
        CharacterLocation.objects.create(
            character=self.character,
            location=self.home,
            role=CharacterLocation.Role.HOME,
            is_primary=True,
        )
        CharacterLocation.objects.create(
            character=self.character,
            location=self.work,
            role=CharacterLocation.Role.WORK,
            is_primary=True,
        )

        props = self.properties()
        # building_type, not the building's bookkeeping name (see
        # _primary_location_type) - the frontend maps this to a plain label
        # ("House", "Bakery", ...) the same way a building's own tooltip does.
        self.assertEqual(props["home_type"], "residential")
        self.assertEqual(props["work_type"], "bakery")

    def test_no_current_activity_scheduled(self):
        props = self.properties()
        self.assertIsNone(props["current_activity"])

    def test_is_moving_reflects_character_state(self):
        self.assertFalse(self.properties()["is_moving"])

        self.character.is_moving = True
        self.character.save(update_fields=["is_moving"])

        self.assertTrue(self.properties()["is_moving"])

    def test_current_activity_uses_present_tense_narrative(self):
        activity_definition = ActivityDefinition.objects.create(
            name="Deliver goods to neighbours",
            present_tense="delivering goods to neighbours",
            kind=ActivityDefinition.Kind.WORK,
        )
        now = timezone.now()
        CharacterActivity.objects.create(
            character=self.character,
            activity_definition=activity_definition,
            scheduled_start=now - timezone.timedelta(minutes=30),
            scheduled_end=now + timezone.timedelta(minutes=30),
        )

        # present_tense, not name/kind - the frontend shows this verbatim
        # in the character's tooltip ("Currently: delivering goods to
        # neighbours").
        self.assertEqual(
            self.properties()["current_activity"], "delivering goods to neighbours"
        )

    def test_current_activity_falls_back_to_lowercased_name(self):
        activity_definition = ActivityDefinition.objects.create(
            name="General labour", kind=ActivityDefinition.Kind.WORK
        )
        now = timezone.now()
        CharacterActivity.objects.create(
            character=self.character,
            activity_definition=activity_definition,
            scheduled_start=now - timezone.timedelta(minutes=30),
            scheduled_end=now + timezone.timedelta(minutes=30),
        )

        # No present_tense authored yet - falls back to a lowercased name
        # (see ActivityDefinition.narrative) rather than crashing/blanking.
        self.assertEqual(self.properties()["current_activity"], "general labour")

    def test_current_activity_ignores_activities_outside_their_scheduled_window(self):
        activity_definition = ActivityDefinition.objects.create(
            name="Sleeping", kind=ActivityDefinition.Kind.SLEEP
        )
        now = timezone.now()
        CharacterActivity.objects.create(
            character=self.character,
            activity_definition=activity_definition,
            scheduled_start=now - timezone.timedelta(hours=10),
            scheduled_end=now - timezone.timedelta(hours=8),
        )

        self.assertIsNone(self.properties()["current_activity"])

    def test_hunger_label_bands(self):
        self.character.needs.hunger = 0
        self.character.needs.save(update_fields=["hunger"])
        self.assertEqual(self.properties()["hunger_label"], "Well fed")

        self.character.needs.hunger = 50
        self.character.needs.save(update_fields=["hunger"])
        self.assertEqual(self.properties()["hunger_label"], "Hungry")


class CharacterDetailSerializerTest(TestCase):
    """
    CharacterDetailSerializer builds on CharacterPointFeatureSerializer's
    properties (home/work/activity - covered above), so these tests only
    cover what it adds: age, sex, and relationships.
    """

    def setUp(self):
        self.character = Character.objects.create(
            given_name="Alice", sex="Female", location=Point(0, 0, srid=PROJECT_SRID)
        )

    def properties(self):
        character = (
            Character.objects.select_related("needs")
            .prefetch_related("locations__location")
            .get(pk=self.character.pk)
        )
        return CharacterDetailSerializer(character).data

    def test_includes_age_and_sex(self):
        props = self.properties()
        self.assertEqual(props["sex"], "Female")
        self.assertIsInstance(props["age"], int)

    def test_no_relationships_by_default(self):
        self.assertEqual(self.properties()["relationships"], [])

    def test_household_relationships_are_summarised(self):
        from character.models import RelationshipRole, RelationshipType
        from character.services import relationship_services

        husband = Character.objects.create(given_name="Thomas", sex="Male")
        relationship_services.relationship_create(
            RelationshipType.MARRIAGE,
            [
                (self.character, RelationshipRole.SPOUSE),
                (husband, RelationshipRole.SPOUSE),
            ],
        )
        daughter = Character.objects.create(given_name="Emily", sex="Female")
        relationship_services.relationship_create(
            RelationshipType.PARENT_CHILD,
            [
                (self.character, RelationshipRole.PARENT),
                (daughter, RelationshipRole.CHILD),
            ],
        )

        relationships = self.properties()["relationships"]
        self.assertCountEqual(
            relationships,
            [
                {"character_id": husband.id, "name": "Thomas", "label": "husband"},
                {"character_id": daughter.id, "name": "Emily", "label": "daughter"},
            ],
        )


class SubzoneFeatureSerializerTest(TestCase):
    def setUp(self):
        centre = PopulationCentre.objects.create(
            name="Testville", location=Point(0, 0, srid=PROJECT_SRID)
        )
        land_area = LandArea.objects.create(
            name="Testville Land Area", population_centre=centre, size=1.0
        )
        self.subzone = Subzone.objects.create(
            name="Testville - Crops",
            land_area=land_area,
            usage="crops",
            size=0.6,
            boundary=SQUARE,
        )

    def properties(self):
        subzone = Subzone.objects.select_related("field_crop").get(pk=self.subzone.pk)
        return SubzoneFeatureSerializer(subzone).data["properties"]

    def test_no_field_crop_yet(self):
        props = self.properties()
        self.assertIsNone(props["crop_stage"])
        self.assertIsNone(props["crop_progress"])
        self.assertIsNone(props["shelter_building_id"])

    def test_fallow_stage(self):
        shelter = Building.objects.create(name="Shelter", building_type="field_shelter")
        FieldCrop.objects.create(
            subzone=self.subzone, shelter_building=shelter, stage=FieldCrop.Stage.FALLOW
        )
        props = self.properties()
        self.assertEqual(props["crop_stage"], "fallow")
        self.assertIsNone(props["crop_progress"])
        self.assertEqual(props["shelter_building_id"], shelter.id)

    def test_growing_stage_progress_between_zero_and_one(self):
        shelter = Building.objects.create(name="Shelter", building_type="field_shelter")
        FieldCrop.objects.create(
            subzone=self.subzone,
            shelter_building=shelter,
            stage=FieldCrop.Stage.GROWING,
            planted_at=timezone.now(),
        )
        props = self.properties()
        self.assertEqual(props["crop_stage"], "growing")
        self.assertAlmostEqual(props["crop_progress"], 0.0, places=2)

    def test_ready_stage(self):
        shelter = Building.objects.create(name="Shelter", building_type="field_shelter")
        FieldCrop.objects.create(
            subzone=self.subzone, shelter_building=shelter, stage=FieldCrop.Stage.READY
        )
        props = self.properties()
        self.assertEqual(props["crop_stage"], "ready")
        self.assertIsNone(props["crop_progress"])

    def test_square_usage_has_no_crop_properties(self):
        square = Subzone.objects.create(
            name="Testville - Square",
            land_area=self.subzone.land_area,
            usage="square",
            size=0.2,
            boundary=SQUARE,
        )
        square = Subzone.objects.select_related("field_crop").get(pk=square.pk)
        props = SubzoneFeatureSerializer(square).data["properties"]
        self.assertEqual(props["usage"], "square")
        self.assertIsNone(props["crop_stage"])
        self.assertIsNone(props["crop_progress"])
        self.assertIsNone(props["shelter_building_id"])


class PopulationCentreLabelFeatureSerializerTest(TestCase):
    """
    The marker feature MapViewportView sends for each village on the
    cross-village map (see issue #673) - needs state/progress alongside the
    name/id it already carried, so the frontend can colour each marker by
    state without an extra per-village fetch.
    """

    def setUp(self):
        self.centre = PopulationCentre.objects.create(
            name="Testville", location=Point(0, 0, srid=PROJECT_SRID)
        )

    def properties(self):
        return PopulationCentreLabelFeatureSerializer(self.centre).data["properties"]

    def test_includes_state_and_progress_with_no_residents(self):
        props = self.properties()
        self.assertEqual(props["name"], "Testville")
        self.assertEqual(props["population_centre_id"], self.centre.id)
        self.assertEqual(props["state"], "Struggling")
        self.assertEqual(props["progress"], 0)

    def test_reflects_village_points_derived_state(self):
        from character.models import Character, PlayerCharacterLink

        resident = Character.objects.create(
            given_name="Res", population_centre=self.centre
        )
        user = user_factory(with_player=True)
        # Deactivate the auto-assigned link/character so only `resident`
        # (with a controllable link_points via days_linked) counts here.
        for link in PlayerCharacterLink.objects.filter(
            player=user.player, is_active=True
        ):
            link.unlink()
        link = PlayerCharacterLink.objects.create(
            player=user.player, character=resident
        )
        link.linked_at = timezone.now() - timezone.timedelta(days=10)
        link.save(update_fields=["linked_at"])

        # village_points is a cached_property read fresh per PopulationCentre
        # instance, so re-fetch rather than reuse self.centre.
        centre = PopulationCentre.objects.get(pk=self.centre.pk)
        props = PopulationCentreLabelFeatureSerializer(centre).data["properties"]

        self.assertEqual(props["state"], centre.state)
        self.assertEqual(props["progress"], centre.progress)
