from __future__ import annotations

import random
from collections import defaultdict, deque
from functools import cached_property
from typing import Optional

from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point
from django.db import transaction
from django.utils import timezone

from locations.constants import PROJECT_SRID


class PathGraph:
    """Undirected node adjacency built from every Path row in one query,
    loaded lazily on first use. find_path BFSes over this in memory rather
    than calling Node.neighbours() per visited node (one query per node -
    an N+1 Sentry flagged in commute_tick). Callers routing many characters
    in one go (commute_tick) share one instance so the graph loads once.
    """

    @cached_property
    def adjacency(self) -> dict[int, set[int]]:
        from locations.models import Path

        adjacency = defaultdict(set)
        for from_id, to_id in Path.objects.values_list("from_node_id", "to_node_id"):
            adjacency[from_id].add(to_id)
            adjacency[to_id].add(from_id)
        return adjacency


def find_path(start_node, end_node, graph: Optional[PathGraph] = None):
    """BFS (fewest hops) from start_node to end_node over the Path graph.
    Returns the list of Nodes along the route, or None if unreachable."""
    if start_node.pk == end_node.pk:
        return [start_node]

    adjacency = (graph or PathGraph()).adjacency
    parents = {start_node.pk: None}
    queue = deque([start_node.pk])

    while queue:
        node_id = queue.popleft()
        if node_id == end_node.pk:
            break
        for neighbour_id in adjacency.get(node_id, ()):
            if neighbour_id not in parents:
                parents[neighbour_id] = node_id
                queue.append(neighbour_id)
    else:
        return None

    path_ids = []
    node_id = end_node.pk
    while node_id is not None:
        path_ids.append(node_id)
        node_id = parents[node_id]
    path_ids.reverse()

    from locations.models import Node

    nodes_by_id = Node.objects.in_bulk(path_ids[1:-1])
    nodes_by_id[start_node.pk] = start_node
    nodes_by_id[end_node.pk] = end_node
    return [nodes_by_id[node_id] for node_id in path_ids]


def go_home(character) -> bool:
    home_building = character.home
    if not home_building:
        print(f"{character.name} has no home to go to!")
        return False

    from locations.models import Node

    destination_node = Node.objects.filter(
        building=home_building, kind=Node.Kind.BUILDING_ENTRANCE
    ).first()

    if not destination_node:
        print(f"{character.name} has no node! Skipping.")
        return False

    rooms = list(home_building.interiorspaces.all())
    room_node = None
    if rooms:
        room = random.choice(rooms)
        room_node = room.nodes.first()
    if room_node:
        destination_node = room_node

    if character.current_node_id == destination_node.id:
        print(f"{character.name} cannot go home, they're already there!")
        return False

    set_destination(character, node=destination_node)
    print(f"{character.name} is going home.")
    return True


def get_nearby_outside_nodes(character, radius: float = 50):
    if not character.location:
        from locations.models import Node

        return Node.objects.none()

    pc = None
    if character.current_node:
        pc = character.current_node.pc

    from locations.models import Node

    qs = Node.objects.filter(kind=Node.Kind.OUTSIDE)

    if pc is not None:
        qs = qs.filter(population_centre=pc)

    qs = qs.annotate(dist=Distance("location", character.location)).order_by("dist")

    qs = qs.filter(dist__lte=radius)

    limit = 10
    qs = qs[:limit]

    return qs


def pick_random_outside_node(character, radius: float = 50) -> Optional[object]:
    nodes = list(get_nearby_outside_nodes(character, radius=radius))
    return random.choice(nodes) if nodes else None


def go_outside(character, radius: float = 100) -> bool:
    node = pick_random_outside_node(character, radius=radius)
    if not node:
        print(f"{character.name} couldn't find anywhere to go outside")
        return False

    set_destination(character, node=node)
    return True


def set_destination(character, *, node=None, obj=None, point=None, graph=None):
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

    if not character.current_node:
        raise ValueError("Character has no current_node")

    path = find_path(character.current_node, target_node, graph=graph)
    if not path:
        raise ValueError(
            f"No path found from {character.current_node} to {target_node}"
        )

    with transaction.atomic():
        active_journey = Journey.objects.filter(
            character=character, status=Journey.Status.ACTIVE
        ).first()
        if active_journey:
            active_journey.cancel()
        Journey.objects.create(
            character=character,
            start_node=character.current_node,
            destination_node=target_node,
            path_nodes=[node.pk for node in path],
            current_index=0,
        )

        character.is_moving = True
        character.target_node = target_node
        character.save(update_fields=["is_moving", "target_node"])

    move_characters_tick.apply_async()


def step_toward(character, time_delta: float = 1.0, speed_modifier: float = 1.0):
    from locations.models import Journey

    journey = getattr(character, "_journey", None)
    if journey is None:
        journey = (
            Journey.objects.filter(character=character, status=Journey.Status.ACTIVE)
            .order_by("-id")
            .first()
        )

    if not journey or journey.is_complete:
        character.is_moving = False
        return False

    character._journey = journey

    # Budget for this tick, spent across as many nodes as it reaches rather
    # than being dropped when a single segment is shorter than the budget -
    # otherwise a character crossing several short segments in one tick
    # visibly slows down at each node instead of moving at a constant speed.
    remaining_distance = character.movement_speed * speed_modifier * time_delta

    while remaining_distance > 0:
        next_node = journey.next_node()
        if not next_node:
            arrive(character, journey)
            return False

        dx = next_node.location.x - character.location.x
        dy = next_node.location.y - character.location.y
        distance = (dx**2 + dy**2) ** 0.5

        if distance <= remaining_distance:
            character.location = Point(
                next_node.location.x, next_node.location.y, srid=PROJECT_SRID
            )
            character.current_node = next_node
            journey.advance_node()
            remaining_distance -= distance

            if journey.is_complete:
                arrive(character, journey)
                return False
        else:
            factor = remaining_distance / distance
            new_x = character.location.x + dx * factor
            new_y = character.location.y + dy * factor
            character.location = Point(new_x, new_y, srid=PROJECT_SRID)
            if not character.is_moving:
                character.is_moving = True
            remaining_distance = 0

    return True


def arrive(character, journey) -> bool:
    if not journey:
        return False

    final_node = journey.destination_node

    character.location = final_node.location
    character.current_node = final_node

    journey.status = journey.Status.COMPLETE
    journey.finished_at = timezone.now()
    journey.save(update_fields=["status", "finished_at"])

    character.is_moving = False
    character.target_node = None

    return True
