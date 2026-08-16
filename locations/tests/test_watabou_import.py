from django.contrib.gis.geos import Point, Polygon
from django.test import TestCase

from economy.models import BuildingCapability
from locations.models import LandArea, Node, PopulationCentre, Road, Subzone
from locations.services.watabou_import import import_watabou_village

# Two adjacent square districts (sharing the edge x=10) so their union is a
# single Polygon.
TRADE_DISTRICT = {
    "type": "Polygon",
    "name": "Trade District",
    "coordinates": [[[0, 0], [10, 0], [10, 10], [0, 10]]],
}
MILL_WARD = {
    "type": "Polygon",
    "name": "Mill Ward",
    "coordinates": [[[10, 0], [20, 0], [20, 10], [10, 10]]],
}
# Building coordinates are a list of rings (one ring each here), same shape
# as watabou's own "buildings" feature - not a bare list of points.
TRADE_BUILDING = [[[2, 2], [8, 2], [8, 8], [2, 8]]]
# A much larger footprint than TRADE_BUILDING (100 sqm vs 36 sqm) - used
# where a test needs population_estimation to produce a population above
# SMALL_SETTLEMENT_POPULATION_THRESHOLD, since TRADE_BUILDING alone rounds
# down to 0 estimated residents per building.
LARGE_BUILDING = [[[0, 0], [10, 0], [10, 10], [0, 10]]]

EARTH = {"coordinates": [[[-500, -500], [500, -500], [500, 500], [-500, 500]]]}


def _make_export(
    *,
    districts=None,
    buildings=None,
    roads=None,
    road_width=None,
    fields=None,
    squares=None,
):
    features = [
        {"type": "Feature", "id": "earth", **EARTH},
        {
            "type": "Feature",
            "id": "buildings",
            "coordinates": buildings if buildings is not None else [],
        },
        {
            "type": "Feature",
            "id": "roads",
            "geometries": roads if roads is not None else [],
        },
    ]
    if road_width is not None:
        features.append({"type": "Feature", "id": "values", "roadWidth": road_width})
    if districts is not None:
        features.append({"type": "Feature", "id": "districts", "geometries": districts})
    if fields is not None:
        features.append({"type": "MultiPolygon", "id": "fields", "coordinates": fields})
    if squares is not None:
        features.append(
            {"type": "MultiPolygon", "id": "squares", "coordinates": squares}
        )
    return {"features": features}


class WatabouImportBoundaryTest(TestCase):
    def test_boundary_is_union_of_all_districts_not_just_the_first(self):
        data = _make_export(districts=[TRADE_DISTRICT, MILL_WARD])
        origin = Point(0, 0, srid=3857)

        centre = import_watabou_village(data, name="Twin Wards", origin=origin)

        # The two 10x10 districts share an edge, so their union covers 200
        # sq units - taking only geometries[0] would give 100.
        self.assertAlmostEqual(centre.boundary.area, 200.0, places=3)

    def test_boundary_falls_back_to_earth_when_no_districts(self):
        data = _make_export(districts=None)
        origin = Point(0, 0, srid=3857)

        centre = import_watabou_village(data, name="No Wards", origin=origin)

        self.assertAlmostEqual(centre.boundary.area, 1000 * 1000, places=1)

    def test_boundary_is_centred_on_origin(self):
        data = _make_export(districts=[TRADE_DISTRICT, MILL_WARD])
        origin = Point(500, -250, srid=3857)

        centre = import_watabou_village(data, name="Offset Wards", origin=origin)

        self.assertAlmostEqual(centre.boundary.centroid.x, origin.x, places=3)
        self.assertAlmostEqual(centre.boundary.centroid.y, origin.y, places=3)


class WatabouImportBuildingTypeTest(TestCase):
    def test_single_building_defaults_to_residential(self):
        data = _make_export(districts=None, buildings=[TRADE_BUILDING])
        origin = Point(0, 0, srid=3857)

        centre = import_watabou_village(data, name="Solo", origin=origin)

        building = centre.buildings.get()
        self.assertEqual(building.building_type, "residential")

    def test_roughly_three_quarters_residential_with_one_of_each_special(self):
        # 8 buildings: 75% -> 6 residential, remaining 2 -> granary plus one
        # shared "communal" building packing both milling and baking (only
        # one non-residential slot is left once granary takes the other),
        # rather than a decorative "inn" - the always-present economy chain
        # is guaranteed a slot ahead of decorative types (see
        # _assign_building_types_and_capabilities).
        data = _make_export(districts=None, buildings=[TRADE_BUILDING] * 8)
        origin = Point(0, 0, srid=3857)

        centre = import_watabou_village(data, name="Eight Buildings", origin=origin)

        types = [b.building_type for b in centre.buildings.order_by("id")]
        self.assertEqual(types.count("residential"), 6)
        self.assertEqual(types.count("granary"), 1)
        self.assertEqual(types.count("communal"), 1)
        for untouched_type in ["inn", "mill", "bakery", "market", "hall"]:
            self.assertEqual(types.count(untouched_type), 0)

        communal = centre.buildings.get(building_type="communal")
        activities = set(communal.capabilities.values_list("activity", flat=True))
        self.assertEqual(activities, {"milling", "baking"})

    def test_leftover_after_every_special_type_falls_back_to_residential(self):
        # 30 small (TRADE_BUILDING) buildings: 75% -> 22 residential
        # (Python's round-half-to-even), remaining 8. TRADE_BUILDING's tiny
        # footprint rounds down to 0 estimated residents per building, so
        # the settlement is well under SMALL_SETTLEMENT_POPULATION_THRESHOLD
        # and milling+baking still share one communal building even though
        # there'd be enough slots for two dedicated ones - granary and
        # communal take 2 of the 8 remaining slots, inn/market/hall take
        # the next 3, and the final 3 fold back into residential (no
        # catch-all).
        data = _make_export(districts=None, buildings=[TRADE_BUILDING] * 30)
        origin = Point(0, 0, srid=3857)

        centre = import_watabou_village(data, name="Thirty Buildings", origin=origin)

        types = [b.building_type for b in centre.buildings.order_by("id")]
        self.assertEqual(types.count("residential"), 25)
        self.assertEqual(types.count("granary"), 1)
        self.assertEqual(types.count("communal"), 1)
        for special_type in ["inn", "market", "hall"]:
            self.assertEqual(types.count(special_type), 1)
        for untouched_type in ["mill", "bakery"]:
            self.assertEqual(types.count(untouched_type), 0)

        communal = centre.buildings.get(building_type="communal")
        activities = set(communal.capabilities.values_list("activity", flat=True))
        self.assertEqual(activities, {"milling", "baking"})

    def test_large_population_gets_dedicated_mill_and_bakery(self):
        # 24 large (LARGE_BUILDING) buildings: 75% -> 18 residential,
        # remaining 6. LARGE_BUILDING's footprint is big enough that the
        # estimated population clears SMALL_SETTLEMENT_POPULATION_THRESHOLD,
        # so milling and baking get dedicated buildings rather than sharing
        # a communal one, even though sharing would also fit.
        data = _make_export(districts=None, buildings=[LARGE_BUILDING] * 24)
        origin = Point(0, 0, srid=3857)

        centre = import_watabou_village(data, name="Large Village", origin=origin)

        types = [b.building_type for b in centre.buildings.order_by("id")]
        self.assertEqual(types.count("granary"), 1)
        self.assertEqual(types.count("mill"), 1)
        self.assertEqual(types.count("bakery"), 1)
        self.assertEqual(types.count("communal"), 0)

        mill = centre.buildings.get(building_type="mill")
        bakery = centre.buildings.get(building_type="bakery")
        self.assertEqual(
            list(mill.capabilities.values_list("activity", flat=True)), ["milling"]
        )
        self.assertEqual(
            list(bakery.capabilities.values_list("activity", flat=True)), ["baking"]
        )

    def test_small_village_packs_milling_and_baking_onto_one_communal_building(self):
        # 6 buildings: 75% -> 4 residential, remaining 2 - not enough for a
        # granary plus one dedicated building per role, so milling and
        # baking share a single "communal" building instead of one losing
        # out to a fixed allocation order (the original Ashenford bug: a
        # small village silently missing a bakery).
        data = _make_export(districts=None, buildings=[TRADE_BUILDING] * 6)
        origin = Point(0, 0, srid=3857)

        centre = import_watabou_village(data, name="Small Village", origin=origin)

        types = [b.building_type for b in centre.buildings.order_by("id")]
        self.assertEqual(types.count("residential"), 4)
        self.assertEqual(types.count("granary"), 1)
        self.assertEqual(types.count("communal"), 1)
        for untouched_type in ["inn", "mill", "bakery", "market", "hall"]:
            self.assertEqual(types.count(untouched_type), 0)

        communal = centre.buildings.get(building_type="communal")
        activities = set(communal.capabilities.values_list("activity", flat=True))
        self.assertEqual(activities, {"milling", "baking"})


class WatabouImportPopulationPlanLoggingTest(TestCase):
    """
    Step 3 of .claude/plans/village-capacity-sizing-plan.md: import logs the
    population-estimation-driven settlement_plan recommendation, but doesn't
    yet act on it - no building/capability assignment changes here. This
    just checks the compute-and-log call doesn't crash and reports a
    sensible number, not any generation-behaviour change.
    """

    def test_import_logs_recommended_settlement_plan(self):
        data = _make_export(districts=None, buildings=[TRADE_BUILDING] * 8)
        origin = Point(0, 0, srid=3857)

        with self.assertLogs("general", level="INFO") as logs:
            import_watabou_village(data, name="Logged Village", origin=origin)

        self.assertTrue(any("recommended plan" in message for message in logs.output))


class WatabouImportGraphTest(TestCase):
    def test_creates_centre_node_and_building_nodes(self):
        data = _make_export(
            districts=[TRADE_DISTRICT, MILL_WARD], buildings=[TRADE_BUILDING]
        )
        origin = Point(0, 0, srid=3857)

        centre = import_watabou_village(data, name="Graph Village", origin=origin)

        self.assertEqual(
            Node.objects.filter(
                population_centre=centre, kind=Node.Kind.CENTRE
            ).count(),
            1,
        )
        building = centre.buildings.get()
        self.assertTrue(
            Node.objects.filter(building=building, kind=Node.Kind.BUILDING).exists()
        )
        self.assertTrue(
            Node.objects.filter(
                building=building, kind=Node.Kind.BUILDING_ENTRANCE
            ).exists()
        )

    def test_granary_has_no_entrance_node_but_other_buildings_do(self):
        data = _make_export(districts=None, buildings=[TRADE_BUILDING] * 8)
        origin = Point(0, 0, srid=3857)

        centre = import_watabou_village(data, name="Granary Entrances", origin=origin)

        granary = centre.buildings.get(building_type="granary")
        self.assertFalse(
            Node.objects.filter(
                building=granary, kind=Node.Kind.BUILDING_ENTRANCE
            ).exists()
        )

        self.assertEqual(
            centre.buildings.exclude(building_type="granary")
            .exclude(nodes__kind=Node.Kind.BUILDING_ENTRANCE)
            .count(),
            0,
        )

    def test_imports_roads_with_width_fallback(self):
        roads = [
            {"type": "LineString", "coordinates": [[0, 0], [10, 0]], "width": 4},
            {"type": "LineString", "coordinates": [[0, 5], [10, 5]]},
        ]
        data = _make_export(
            districts=[TRADE_DISTRICT, MILL_WARD], roads=roads, road_width=8
        )
        origin = Point(0, 0, srid=3857)

        centre = import_watabou_village(data, name="Road Village", origin=origin)

        widths = sorted(
            Road.objects.filter(population_centre=centre).values_list(
                "width", flat=True
            )
        )
        self.assertEqual(widths, [4, 8])

    def test_raises_without_district_or_earth_boundary(self):
        data = {
            "features": [
                {"type": "Feature", "id": "buildings", "coordinates": []},
                {"type": "Feature", "id": "roads", "geometries": []},
            ]
        }
        origin = Point(0, 0, srid=3857)

        with self.assertRaises(ValueError):
            import_watabou_village(data, name="No Boundary", origin=origin)


# Two separate 10x10 squares, same shape convention as watabou's own
# "fields" MultiPolygon: a list of polygons, each a list of rings, each ring
# a list of [x, y] points.
FIELD_ONE = [[[200, 200], [210, 200], [210, 210], [200, 210]]]
FIELD_TWO = [[[300, 300], [310, 300], [310, 310], [300, 310]]]


class WatabouImportFieldsTest(TestCase):
    def test_creates_one_crops_subzone_per_field_polygon(self):
        data = _make_export(
            districts=[TRADE_DISTRICT, MILL_WARD], fields=[FIELD_ONE, FIELD_TWO]
        )
        origin = Point(0, 0, srid=3857)

        centre = import_watabou_village(data, name="Fielded Wards", origin=origin)

        land_area = LandArea.objects.get(population_centre=centre)
        subzones = list(land_area.subzones.all())
        self.assertEqual(len(subzones), 2)
        self.assertTrue(all(s.usage == "crops" for s in subzones))

    def test_subzone_size_matches_polygon_area_in_hectares(self):
        data = _make_export(districts=[TRADE_DISTRICT, MILL_WARD], fields=[FIELD_ONE])
        origin = Point(0, 0, srid=3857)

        centre = import_watabou_village(data, name="One Field", origin=origin)

        subzone = LandArea.objects.get(population_centre=centre).subzones.get()
        # A 10x10 square is 100 sq metres = 0.01 hectares.
        self.assertAlmostEqual(subzone.size, 0.01, places=6)

    def test_land_area_boundary_covers_every_field(self):
        data = _make_export(
            districts=[TRADE_DISTRICT, MILL_WARD], fields=[FIELD_ONE, FIELD_TWO]
        )
        origin = Point(0, 0, srid=3857)

        centre = import_watabou_village(data, name="Two Fields", origin=origin)

        land_area = LandArea.objects.get(population_centre=centre)
        for subzone in land_area.subzones.all():
            self.assertTrue(land_area.boundary.intersects(subzone.boundary))

    def test_no_fields_feature_creates_no_land_area(self):
        data = _make_export(districts=[TRADE_DISTRICT, MILL_WARD])
        origin = Point(0, 0, srid=3857)

        centre = import_watabou_village(data, name="No Fields", origin=origin)

        self.assertFalse(LandArea.objects.filter(population_centre=centre).exists())
        self.assertFalse(Subzone.objects.exists())

    def test_empty_fields_coordinates_creates_no_land_area(self):
        data = _make_export(districts=[TRADE_DISTRICT, MILL_WARD], fields=[])
        origin = Point(0, 0, srid=3857)

        centre = import_watabou_village(data, name="Empty Fields", origin=origin)

        self.assertFalse(LandArea.objects.filter(population_centre=centre).exists())


# Reuses FIELD_ONE/FIELD_TWO's shapes for the "squares" MultiPolygon too -
# same convention, different feature id/usage.
SQUARE_ONE = FIELD_ONE
SQUARE_TWO = FIELD_TWO


class WatabouImportSquaresTest(TestCase):
    def test_creates_one_square_subzone_per_square_polygon(self):
        data = _make_export(
            districts=[TRADE_DISTRICT, MILL_WARD], squares=[SQUARE_ONE, SQUARE_TWO]
        )
        origin = Point(0, 0, srid=3857)

        centre = import_watabou_village(data, name="Plaza Wards", origin=origin)

        land_area = LandArea.objects.get(
            population_centre=centre, name__startswith="Squares"
        )
        subzones = list(land_area.subzones.all())
        self.assertEqual(len(subzones), 2)
        self.assertTrue(all(s.usage == "square" for s in subzones))

    def test_squares_and_fields_create_separate_land_areas(self):
        data = _make_export(
            districts=[TRADE_DISTRICT, MILL_WARD],
            fields=[FIELD_ONE],
            squares=[SQUARE_TWO],
        )
        origin = Point(0, 0, srid=3857)

        centre = import_watabou_village(data, name="Mixed Wards", origin=origin)

        self.assertEqual(LandArea.objects.filter(population_centre=centre).count(), 2)
        crop_subzone = Subzone.objects.get(usage="crops")
        square_subzone = Subzone.objects.get(usage="square")
        self.assertNotEqual(crop_subzone.land_area_id, square_subzone.land_area_id)

    def test_no_squares_feature_creates_no_square_subzone(self):
        data = _make_export(districts=[TRADE_DISTRICT, MILL_WARD])
        origin = Point(0, 0, srid=3857)

        centre = import_watabou_village(data, name="No Squares", origin=origin)

        self.assertFalse(
            LandArea.objects.filter(
                population_centre=centre, name__startswith="Squares"
            ).exists()
        )
        self.assertFalse(Subzone.objects.filter(usage="square").exists())
