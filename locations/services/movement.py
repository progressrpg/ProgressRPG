from __future__ import annotations

import random
from typing import Optional

from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point
from django.db import transaction
from django.utils import timezone


def find_path(start_node, end_node):
    # very dumb: pick first outgoing path until we reach the end
    # or you can implement BFS for shortest segment count
    visited = set()
    queue = [(start_node, [start_node])]

    while queue:
        node, path = queue.pop(0)
        if node == end_node:
            return path
        visited.add(node)
        for neighbor in node.neighbours():
            if neighbor not in visited:
                queue.append((neighbor, path + [neighbor]))
    return None


def go_home(movable) -> bool:
    if not movable.building:
        print(f"{movable.name} has no home to go to!")
        return False

    from locations.models import Node

    destination_node = Node.objects.filter(
        building=movable.building, kind=Node.Kind.BUILDING_ENTRANCE
    ).first()

    if not destination_node:
        print(f"{movable.name} has no node! Skipping.")
        return False

    rooms = list(movable.building.interiorspaces.all())
    room_node = None
    if rooms:
        room = random.choice(rooms)
        room_node = room.nodes.first()
    if room_node:
        destination_node = room_node

    if movable.current_node_id == destination_node.id:
        print(f"{movable.name} cannot go home, they're already there!")
        return False

    set_destination(movable, node=destination_node)
    print(f"{movable.name} is going home.")
    return True


def get_nearby_outside_nodes(movable, radius: float = 50):
    if not movable.location:
        from locations.models import Node

        return Node.objects.none()

    pc = None
    if movable.current_node:
        pc = movable.current_node.pc

    from locations.models import Node

    qs = Node.objects.filter(kind=Node.Kind.OUTSIDE)

    if pc is not None:
        qs = qs.filter(population_centre=pc)

    qs = qs.annotate(dist=Distance("location", movable.location)).order_by("dist")

    qs = qs.filter(dist__lte=radius)

    limit = 10
    qs = qs[:limit]

    return qs


def pick_random_outside_node(movable, radius: float = 50) -> Optional[object]:
    nodes = list(get_nearby_outside_nodes(movable, radius=radius))
    return random.choice(nodes) if nodes else None


def go_outside(movable, radius: float = 100) -> bool:
    node = pick_random_outside_node(movable, radius=radius)
    if not node:
        print(f"{movable.name} couldn't find anywhere to go outside")
        return False

    set_destination(movable, node=node)
    return True


def set_destination(movable, *, node=None, obj=None, point=None):
    from locations.models import Journey, Node
    from locations.tasks import move_characters_tick

    if node is not None:
        target_node = node
    elif obj is not None:
        target_node = Node.objects.filter(building=obj).get()
    elif point is not None:
        target_node = (
            Node.objects.annotate(distance=Distance("location", point))
            .order_by("distance")
            .first()
        )
    else:
        raise ValueError("Must provide node, obj, or point")

    if not target_node:
        raise ValueError("Could not resolve target node")

    if not movable.current_node:
        raise ValueError("Movable has no current_node")

    path = find_path(movable.current_node, target_node)
    if not path:
        raise ValueError(f"No path found from {movable.current_node} to {target_node}")

    with transaction.atomic():
        active_journey = Journey.objects.filter(
            character=movable, status="active"
        ).first()
        if active_journey:
            active_journey.cancel()
        Journey.objects.create(
            character=movable,
            start_node=movable.current_node,
            destination_node=target_node,
            path_nodes=[node.pk for node in path],
            current_index=0,
        )

        movable.is_moving = True
        movable.target_node = target_node
        movable.save(update_fields=["is_moving", "target_node"])

    move_characters_tick.apply_async()


def step_toward(movable, time_delta: float = 1.0, speed_modifier: float = 1.0):
    from locations.models import Journey

    journey = getattr(movable, "_journey", None)
    if journey is None:
        journey = (
            Journey.objects.filter(character=movable, status="active")
            .order_by("-id")
            .first()
        )

    if not journey or journey.is_complete:
        movable.is_moving = False
        return False

    movable._journey = journey
    next_node = journey.next_node()
    if not next_node:
        arrive(movable, journey)
        return False

    dx = next_node.location.x - movable.location.x
    dy = next_node.location.y - movable.location.y
    distance = (dx**2 + dy**2) ** 0.5
    max_distance = movable.movement_speed * speed_modifier * time_delta

    if distance <= max_distance:
        movable.location = Point(next_node.location.x, next_node.location.y, srid=3857)

        movable.current_node = next_node
        journey.advance_node()

        if journey.is_complete:
            arrive(movable, journey)
            return False
    else:
        factor = max_distance / distance
        new_x = movable.location.x + dx * factor
        new_y = movable.location.y + dy * factor
        movable.location = Point(new_x, new_y, srid=3857)
        if not movable.is_moving:
            movable.is_moving = True

    return True


def arrive(movable, journey) -> bool:
    if not journey:
        return False

    from django.contrib.contenttypes.models import ContentType

    final_node = journey.destination_node

    movable.location = final_node.location
    movable.current_node = final_node

    journey.status = "complete"
    journey.finished_at = timezone.now()
    journey.save(update_fields=["status", "finished_at"])

    movable.is_moving = False
    movable.target_node = None

    if final_node.building_id:
        movable.current_content_type = ContentType.objects.get_for_model(
            final_node.building
        )
        movable.current_object_id = final_node.building_id
    else:
        movable.current_content_type = None
        movable.current_object_id = None

    return True
