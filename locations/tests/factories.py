from django.contrib.gis.geos import Point, Polygon

from locations.management.commands.generate_villages import create_building_footprint
from locations.models import Building, PopulationCentre

# Shared village boundary used by tests that need a character to move/wander
# within a fixed area - a simple 100x100 square centred on the origin.
VILLAGE_BOUNDARY = Polygon(
    ((-50, -50), (-50, 50), (50, 50), (50, -50), (-50, -50)), srid=3857
)


def make_centre_with_building(name, centre_point: Point) -> PopulationCentre:
    """Minimal PopulationCentre + one Building, boundary sized like generate_villages."""
    footprint = create_building_footprint(centre_point, min_size=10, max_size=20)
    boundary = footprint.buffer(10)
    centre = PopulationCentre.objects.create(
        name=name, location=centre_point, boundary=boundary
    )
    Building.objects.create(
        name=f"House of {name}",
        building_type="residential",
        location=centre_point,
        footprint=footprint,
        population_centre=centre,
    )
    return centre
