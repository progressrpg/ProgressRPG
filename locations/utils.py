import math
import random
from django.contrib.gis.geos import Point, Polygon


class InvalidBBoxError(ValueError):
    """Raised when a `?bbox=` query param is missing, malformed, or too large."""


# Villages are seeded 1000-2000 units (metres, srid 3857) apart from each
# other (see min_centre_distance/max_centre_distance in generate_villages.py).
# 10km per side comfortably covers many villages in one viewport while still
# rejecting a request for "the entire world" in one query, since every
# feature in the bbox gets fully serialized (no vector-tile-style paging).
MAX_BBOX_AREA_SQ_M = 10_000 * 10_000

# Padding added around the world's outermost population-centre geometry when
# computing the map's pan bounds (MapWorldBoundsView) - keeps a village from
# sitting flush against the edge of where the camera can pan, rather than
# clamping panning exactly at its boundary/location extent.
WORLD_BOUNDS_PADDING_M = 500


def parse_bbox_param(raw_bbox: str | None) -> Polygon:
    """
    Parse a `?bbox=minx,miny,maxx,maxy` query param (same units as stored
    geometry, i.e. srid 3857 metres) into a GEOS Polygon usable for spatial
    lookups. Raises InvalidBBoxError on anything missing/malformed/oversized.
    """
    if not raw_bbox:
        raise InvalidBBoxError("bbox query parameter is required")

    parts = raw_bbox.split(",")
    if len(parts) != 4:
        raise InvalidBBoxError("bbox must have exactly 4 comma-separated values")

    try:
        minx, miny, maxx, maxy = (float(p) for p in parts)
    except ValueError:
        raise InvalidBBoxError("bbox values must be numbers")

    if minx >= maxx or miny >= maxy:
        raise InvalidBBoxError("bbox min values must be less than max values")

    area = (maxx - minx) * (maxy - miny)
    if area > MAX_BBOX_AREA_SQ_M:
        raise InvalidBBoxError("bbox area exceeds the maximum allowed - zoom in")

    bbox = Polygon.from_bbox((minx, miny, maxx, maxy))
    bbox.srid = 3857
    return bbox


def compass_direction(angle_deg):
    directions = ["E", "NE", "N", "NW", "W", "SW", "S", "SE"]
    idx = round(angle_deg / 45) % 8
    return directions[idx]


def relative_distance_direction(pc_location: Point, obj_location: Point):
    """
    Returns distance and angle of obj relative to the population centre.
    Angle in degrees: 0° = east, 90° = north.
    """
    dx = obj_location.x - pc_location.x
    dy = obj_location.y - pc_location.y
    distance = math.sqrt(dx**2 + dy**2)
    angle_rad = math.atan2(dy, dx)  # returns -pi..pi
    angle_deg = math.degrees(angle_rad) % 360  # normalize 0..360
    direction = compass_direction(angle_deg)
    return distance, direction


def rotate_point(
    x: float, y: float, origin_x: float, origin_y: float, angle_deg: float
):
    """Rotate (x, y) by angle_deg degrees around (origin_x, origin_y)."""
    angle_rad = math.radians(angle_deg)
    dx, dy = x - origin_x, y - origin_y
    cos_a, sin_a = math.cos(angle_rad), math.sin(angle_rad)
    return (
        origin_x + dx * cos_a - dy * sin_a,
        origin_y + dx * sin_a + dy * cos_a,
    )


def perturb_quad_corners(
    corners: list[tuple[float, float]], width: float, height: float, irregularity: float
) -> list[tuple[float, float]]:
    """
    Randomly jitter each corner of a quadrilateral, scaled by width/height, to
    break up a perfectly rectangular shape (building footprints, field
    plots). No-op when irregularity is 0.
    """
    if irregularity <= 0:
        return corners

    max_dx = width * irregularity
    max_dy = height * irregularity
    return [
        (cx + random.uniform(-max_dx, max_dx), cy + random.uniform(-max_dy, max_dy))
        for cx, cy in corners
    ]


def create_hub_and_spoke(self, central_node, nodes_to_connect):
    """
    Create hub-and-spoke paths between central_node and nodes_to_connect.
    """
    from locations.models import Path

    paths = []
    # 1 Create hub-and-spoke connections
    for node in nodes_to_connect:
        if node == central_node:
            continue
        path1, _ = Path.objects.get_or_create(from_node=node, to_node=central_node)
        path2, _ = Path.objects.get_or_create(from_node=central_node, to_node=node)
        paths.extend([path1, path2])

    return paths
