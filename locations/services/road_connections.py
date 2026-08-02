"""
Draws a purely cosmetic Road between a newly imported village and its
nearest neighbour, connecting the closest pair of road endpoints across the
two villages. This is rendering-only - see the Road model's own docstring
for why it isn't wired into the Node/Path movement graph - there's no
gameplay support for travelling between villages yet, so the point is just
to stop villages looking isolated on the map.
"""

from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import LineString, Point

from locations.models import PopulationCentre, Road

CONNECTOR_ROAD_WIDTH = 4.0


def _road_endpoints(population_centre: PopulationCentre) -> list[Point]:
    endpoints = []
    for road in population_centre.roads.all():
        coords = road.geom.coords
        endpoints.append(Point(*coords[0], srid=road.geom.srid))
        endpoints.append(Point(*coords[-1], srid=road.geom.srid))
    return endpoints


def connect_nearest_village_roads(population_centre: PopulationCentre) -> Road | None:
    """
    Find the nearest other PopulationCentre that has at least one Road, and
    draw a new Road straight between whichever pair of road endpoints (one
    from each village) is closest. Returns None if this village has no
    roads of its own, or no such neighbour exists.
    """
    own_endpoints = _road_endpoints(population_centre)
    if not own_endpoints:
        return None

    neighbour = (
        PopulationCentre.objects.exclude(pk=population_centre.pk)
        .filter(roads__isnull=False)
        .distinct()
        .annotate(distance=Distance("location", population_centre.location))
        .order_by("distance")
        .first()
    )
    if neighbour is None:
        return None

    neighbour_endpoints = _road_endpoints(neighbour)

    closest_pair = min(
        ((a, b) for a in own_endpoints for b in neighbour_endpoints),
        key=lambda pair: pair[0].distance(pair[1]),
    )

    return Road.objects.create(
        geom=LineString(closest_pair[0], closest_pair[1], srid=closest_pair[0].srid),
        width=CONNECTOR_ROAD_WIDTH,
    )
