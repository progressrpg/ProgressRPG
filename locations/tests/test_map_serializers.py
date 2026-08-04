from django.contrib.gis.geos import Point, Polygon
from django.test import TestCase
from django.utils import timezone

from character.models import Character, CharacterLocation
from economy.models import FieldCrop, GoodsStock

from ..models import Building, LandArea, PopulationCentre, Subzone
from ..serializers import (
    BuildingFeatureSerializer,
    CharacterPointFeatureSerializer,
    PopulationCentreLabelFeatureSerializer,
    SubzoneFeatureSerializer,
)

SQUARE = Polygon(
    ((0, 0), (0, 10), (10, 10), (10, 0), (0, 0)),
    srid=3857,
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
        worker = Character.objects.create(first_name="Worker", last_name="Bee")
        CharacterLocation.objects.create(
            character=worker,
            location=self.building,
            role=CharacterLocation.Role.WORK,
            is_primary=True,
        )
        not_primary = Character.objects.create(first_name="Substitute", last_name="Bee")
        CharacterLocation.objects.create(
            character=not_primary,
            location=self.building,
            role=CharacterLocation.Role.WORK,
            is_primary=False,
        )
        home_only = Character.objects.create(first_name="Resident", last_name="Bee")
        CharacterLocation.objects.create(
            character=home_only,
            location=self.building,
            role=CharacterLocation.Role.HOME,
            is_primary=True,
        )

        props = self.properties()
        self.assertEqual(props["workers"], 1)
        self.assertEqual(props["residents"], 1)

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
            first_name="Alice", last_name="Smith", location=Point(0, 0, srid=3857)
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
        self.assertIsNone(props["home"])
        self.assertIsNone(props["work"])

    def test_home_and_work_from_primary_locations_only(self):
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
        self.assertEqual(props["home"], "Rose Cottage")
        self.assertEqual(props["work"], "Village Bakery")

    def test_hunger_label_bands(self):
        self.character.needs.hunger = 0
        self.character.needs.save(update_fields=["hunger"])
        self.assertEqual(self.properties()["hunger_label"], "Well fed")

        self.character.needs.hunger = 50
        self.character.needs.save(update_fields=["hunger"])
        self.assertEqual(self.properties()["hunger_label"], "Hungry")


class SubzoneFeatureSerializerTest(TestCase):
    def setUp(self):
        centre = PopulationCentre.objects.create(
            name="Testville", location=Point(0, 0, srid=3857)
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

    def test_fallow_stage(self):
        shelter = Building.objects.create(name="Shelter", building_type="field_shelter")
        FieldCrop.objects.create(
            subzone=self.subzone, shelter_building=shelter, stage=FieldCrop.Stage.FALLOW
        )
        props = self.properties()
        self.assertEqual(props["crop_stage"], "fallow")
        self.assertIsNone(props["crop_progress"])

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


class PopulationCentreLabelFeatureSerializerTest(TestCase):
    """
    The marker feature MapViewportView sends for each village on the
    cross-village map (see issue #673) - needs state/progress alongside the
    name/id it already carried, so the frontend can colour each marker by
    state without an extra per-village fetch.
    """

    def setUp(self):
        self.centre = PopulationCentre.objects.create(
            name="Testville", location=Point(0, 0, srid=3857)
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
        from users.models import CustomUser

        resident = Character.objects.create(
            first_name="Res", last_name="Ident", population_centre=self.centre
        )
        user = CustomUser.objects.create_user(email="villager@example.com", password="x")
        # Deactivate the auto-assigned link/character so only `resident`
        # (with a controllable link_points via days_linked) counts here.
        for link in PlayerCharacterLink.objects.filter(player=user.player, is_active=True):
            link.unlink()
        link = PlayerCharacterLink.objects.create(player=user.player, character=resident)
        link.linked_at = timezone.now() - timezone.timedelta(days=10)
        link.save(update_fields=["linked_at"])

        # village_points is a cached_property read fresh per PopulationCentre
        # instance, so re-fetch rather than reuse self.centre.
        centre = PopulationCentre.objects.get(pk=self.centre.pk)
        props = PopulationCentreLabelFeatureSerializer(centre).data["properties"]

        self.assertEqual(props["state"], centre.state)
        self.assertEqual(props["progress"], centre.progress)
