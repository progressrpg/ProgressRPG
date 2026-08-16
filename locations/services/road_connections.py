"""
Draws a purely cosmetic Road between a newly imported village and its
nearest neighbour, connecting the closest pair of road endpoints across the
two villages. This is rendering-only - see the Road model's own docstring
for why it isn't wired into the Node/Path movement graph - there's no
gameplay support for travelling between villages yet, so the point is just
to stop villages looking isolated on the map.
"""

from math import hypot, sin, pi
from random import Random

from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import LineString, Point

from locations.models import PopulationCentre, Road


def _curved_points(
    start: Point, end: Point, *, rng: Random, segments: int = 6
) -> list[Point]:
    dx = end.x - start.x
    dy = end.y - start.y
    length = hypot(dx, dy)

    # Unit vector perpendicular to the road.
    px = -dy / length
    py = dx / length

    curve_amount = min(length * rng.uniform(0.15, 0.25), 100)
    offset = rng.uniform(curve_amount * 0.5, curve_amount)

    if rng.random() < 0.5:
        offset *= -1

    points = []

    for i in range(segments + 1):
        progress = i / segments

        # Smooth curve: 0 at either end, maximum in the middle.
        curve = sin(progress * pi) * offset

        points.append(
            Point(
                start.x + dx * progress + px * curve,
                start.y + dy * progress + py * curve,
                srid=start.srid,
            )
        )

    return points


def curved_connector(start: Point, end: Point) -> LineString:
    dx = end.x - start.x
    dy = end.y - start.y
    length = hypot(dx, dy)

    if length == 0:
        return LineString(start, end, srid=start.srid)

    # Deterministic random so the same villages always get the same road.
    seed = f"{round(start.x)}:{round(start.y)}:{round(end.x)}:{round(end.y)}"
    rng = Random(seed)

    points = _curved_points(start, end, rng=rng)
    return LineString(points, srid=start.srid)


CONNECTOR_ROAD_WIDTH = 6.0


def _road_endpoints(population_centre: PopulationCentre) -> list[Point]:
    endpoints = []
    for road in population_centre.roads.all():
        coords = road.geom.coords
        start = coords[0]
        end = coords[-1]
        endpoints.append(Point(start[0], start[1], srid=road.geom.srid))
        endpoints.append(Point(end[0], end[1], srid=road.geom.srid))
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
        population_centre=population_centre,
        geom=curved_connector(closest_pair[0], closest_pair[1]),
        width=CONNECTOR_ROAD_WIDTH,
    )
