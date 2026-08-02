from django.contrib.gis.geos import Point, Polygon
from django.test import TestCase

from locations.models import LandArea, Node, PopulationCentre, Road, Subzone
from locations.services.watabou_import import import_watabou_village

# Two adjacent square districts (sharing the edge x=10) so their union is a
# single Polygon, plus a residential-shaped one further out to exercise
# both district-based building_type inference and the "no matching
# district" fallback.
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
# A building whose centroid sits outside both districts above.
STRAY_BUILDING = [[[100, 100], [110, 100], [110, 110], [100, 110]]]
TRADE_BUILDING = [[[2, 2], [8, 2], [8, 8], [2, 8]]]
MILL_BUILDING = [[[12, 2], [18, 2], [18, 8], [12, 8]]]

EARTH = {"coordinates": [[[-500, -500], [500, -500], [500, 500], [-500, 500]]]}


def _make_export(
    *, districts=None, buildings=None, roads=None, road_width=None, fields=None
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
    def test_building_type_inferred_from_containing_district_name(self):
        data = _make_export(
            districts=[TRADE_DISTRICT, MILL_WARD],
            buildings=[TRADE_BUILDING, MILL_BUILDING],
        )
        origin = Point(0, 0, srid=3857)

        centre = import_watabou_village(data, name="Typed Wards", origin=origin)

        buildings = {b.name: b.building_type for b in centre.buildings.all()}
        self.assertEqual(buildings["Building 1 of (Typed Wards)"], "communal")
        self.assertEqual(buildings["Building 2 of (Typed Wards)"], "mill")

    def test_building_outside_every_district_defaults_to_residential(self):
        data = _make_export(
            districts=[TRADE_DISTRICT, MILL_WARD], buildings=[STRAY_BUILDING]
        )
        origin = Point(0, 0, srid=3857)

        centre = import_watabou_village(data, name="Stray", origin=origin)

        building = centre.buildings.get()
        self.assertEqual(building.building_type, "residential")

    def test_building_type_defaults_to_residential_with_no_districts(self):
        data = _make_export(districts=None, buildings=[TRADE_BUILDING])
        origin = Point(0, 0, srid=3857)

        centre = import_watabou_village(data, name="No Wards", origin=origin)

        building = centre.buildings.get()
        self.assertEqual(building.building_type, "residential")


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
