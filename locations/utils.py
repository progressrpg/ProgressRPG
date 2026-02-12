import math
from django.contrib.gis.geos import Point


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
