from io import StringIO

from django.contrib.gis.geos import Point, Polygon
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from locations.models import Building, LandArea, Node, PopulationCentre, Road, Subzone
from locations.services.population_centre_admin import delete_population_centre

FOOTPRINT = Polygon(((-5, -5), (-5, 5), (5, 5), (5, -5), (-5, -5)), srid=3857)


def _make_populated_centre(name: str) -> PopulationCentre:
    centre = PopulationCentre.objects.create(
        name=name, location=Point(1, 2, srid=3857), boundary=FOOTPRINT
    )
    building = Building.objects.create(
        name=f"House of {name}",
        building_type="residential",
        location=Point(0, 0, srid=3857),
        footprint=FOOTPRINT,
        population_centre=centre,
    )
    Node.objects.create(
        building=building, kind=Node.Kind.BUILDING, location=building.location
    )
    Node.objects.create(
        name="centre",
        population_centre=centre,
        kind=Node.Kind.CENTRE,
        location=centre.location,
    )
    Road.objects.create(
        population_centre=centre,
        geom=Polygon(
            ((-5, -5), (-5, 5), (5, 5), (5, -5), (-5, -5)), srid=3857
        ).boundary,
    )
    land_area = LandArea.objects.create(
        name=f"Fields of {name}",
        population_centre=centre,
        location=Point(20, 20, srid=3857),
        boundary=Polygon(((15, 15), (15, 25), (25, 25), (25, 15), (15, 15)), srid=3857),
        size=1.0,
    )
    Subzone.objects.create(
        land_area=land_area,
        name=f"Crops of {name}",
        location=land_area.location,
        boundary=land_area.boundary,
        size=1.0,
        usage="crops",
    )
    return centre


class DeletePopulationCentreTest(TestCase):
    def test_deletes_centre_and_everything_inside_it(self):
        centre = _make_populated_centre("Doomed")
        building_id = centre.buildings.get().id
        land_area_id = centre.land_areas.get().id
        subzone_id = Subzone.objects.get(land_area_id=land_area_id).id

        old_location = delete_population_centre("Doomed")

        self.assertEqual(old_location, Point(1, 2, srid=3857))
        self.assertFalse(PopulationCentre.objects.filter(name="Doomed").exists())
        self.assertFalse(Building.objects.filter(id=building_id).exists())
        self.assertFalse(Node.objects.filter(building_id=building_id).exists())
        self.assertFalse(Road.objects.filter(population_centre_id=centre.id).exists())
        self.assertFalse(LandArea.objects.filter(id=land_area_id).exists())
        self.assertFalse(Subzone.objects.filter(id=subzone_id).exists())

    def test_returns_none_when_no_such_centre(self):
        self.assertIsNone(delete_population_centre("Nonexistent"))


class ManagePopulationCentresCommandTest(TestCase):
    def test_list_shows_each_centre(self):
        _make_populated_centre("Alpha")
        _make_populated_centre("Beta")

        out = StringIO()
        call_command("manage_centres", "--list", stdout=out)

        output = out.getvalue()
        self.assertIn("Alpha", output)
        self.assertIn("Beta", output)

    def test_list_reports_when_empty(self):
        out = StringIO()
        call_command("manage_centres", "--list", stdout=out)

        self.assertIn("No PopulationCentres found.", out.getvalue())

    def test_shows_help_when_no_flag_given(self):
        out = StringIO()
        call_command("manage_centres", stdout=out)

        self.assertIn("usage:", out.getvalue())

    def test_rejects_both_list_and_delete(self):
        with self.assertRaises(CommandError):
            call_command(
                "manage_centres", "--list", "--delete", "Alpha", stdout=StringIO()
            )

    def test_delete_errors_on_unknown_name(self):
        with self.assertRaises(CommandError):
            call_command(
                "manage_centres",
                "--delete",
                "Nonexistent",
                "--noinput",
                stdout=StringIO(),
            )

    def test_delete_with_noinput_skips_confirmation(self):
        _make_populated_centre("Gone")

        out = StringIO()
        call_command(
            "manage_centres",
            "--delete",
            "Gone",
            "--noinput",
            stdout=out,
        )

        self.assertFalse(PopulationCentre.objects.filter(name="Gone").exists())
        self.assertIn("Deleted 'Gone'", out.getvalue())
