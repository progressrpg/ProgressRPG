from django.contrib.gis.geos import Point, Polygon
from django.test import TestCase

from locations.models import Node, PopulationCentre, Road
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


def _make_export(*, districts=None, buildings=None, roads=None, road_width=None):
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
