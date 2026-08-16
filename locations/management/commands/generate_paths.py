# locations/management/commands/generate_nodes.py
# locations/management/commands/generate_paths.py

import math

from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import LineString, Point
from django.core.management.base import BaseCommand
from django.db import transaction
from django.shortcuts import get_object_or_404

from locations.models import Building, PopulationCentre, Node, Path
from locations.utils import create_hub_and_spoke

# Extra clearance (in metres) added beyond a blocking building's own
# bounding radius when computing a waypoint that routes a path around it.
WAYPOINT_MARGIN = 5
# Number of increasingly-wide waypoint offsets to try before giving up and
# leaving a path as its original straight line.
WAYPOINT_ATTEMPTS = 4


class Command(BaseCommand):
    help = "Generate paths for a population centre using existing nodes."

    def add_arguments(self, parser):
        parser.add_argument(
            "--centre",
            type=int,
            help="Generate for a single population centre ID only.",
        )
        parser.add_argument("--building-neighbours", type=int, default=2)
        parser.add_argument("--outside-neighbours", type=int, default=2)
        parser.add_argument("--poi-neighbours", type=int, default=2)

    @transaction.atomic
    def handle(self, *args, **options):
        centres = PopulationCentre.objects.all()
        if options["centre"]:
            centres = centres.filter(id=options["centre"])

        for centre in centres:
            # Clear paths for this centre
            Path.objects.filter(population_centre=centre).delete()

            central_node = Node.objects.filter(
                population_centre=centre,
                kind=Node.Kind.CENTRE,
            ).first()

            if not central_node:
                self.stdout.write(
                    self.style.WARNING(f"{centre}: no central node; skipping")
                )
                continue

            building_nodes = Node.objects.filter(
                building__population_centre=centre,
                kind=Node.Kind.BUILDING_ENTRANCE,
            )

            if not building_nodes.exists():
                self.stdout.write(
                    self.style.WARNING(f"{centre}: no building nodes; skipping")
                )
                continue

            paths = []
            paths.extend(
                self.create_street_network(
                    central_node, list(building_nodes), options["building_neighbours"]
                )
            )

            outside_nodes = Node.objects.filter(
                population_centre=centre, kind=Node.Kind.OUTSIDE
            )
            poi_nodes = Node.objects.filter(
                population_centre=centre, kind=Node.Kind.POI
            )

            paths.extend(
                self.connect_to_nearest(
                    building_nodes, outside_nodes, options["outside_neighbours"]
                )
            )
            paths.extend(
                self.connect_to_nearest(
                    building_nodes, poi_nodes, options["poi_neighbours"]
                )
            )

            for p in paths:
                p.population_centre = centre
            Path.objects.bulk_update(paths, ["population_centre"])

            self.reroute_paths_around_buildings(paths, centre)

        self.stdout.write(self.style.SUCCESS("Paths generated successfully."))

    def connect_to_nearest(self, building_nodes_qs, other_nodes_qs, max_neighbours=2):
        paths = []
        for node in other_nodes_qs:
            neighbours = building_nodes_qs.annotate(
                dist=Distance("location", node.location)
            ).order_by("dist")[:max_neighbours]
            for bn in neighbours:
                p1, _ = Path.objects.get_or_create(from_node=node, to_node=bn)
                p2, _ = Path.objects.get_or_create(from_node=bn, to_node=node)
                paths.extend([p1, p2])
        return paths

    def create_street_network(self, central_node, building_nodes, max_neighbours=2):
        """
        Connects building nodes to each other to create 'streets',
        while keeping connections to the central node.
        """
        paths = []
        # 1 Create hub-and-spoke connections
        for node in building_nodes:
            paths.extend(create_hub_and_spoke(self, central_node, building_nodes))

        # Connect each building node to its nearest neighbours
        for node in building_nodes:
            if node == central_node:
                continue

            # Exclude itself and the central node
            candidates = [
                n for n in building_nodes if n.pk not in (node.pk, central_node.pk)
            ]

            # Annotate distances and sort
            nearest = sorted(
                candidates, key=lambda n: node.location.distance(n.location)
            )[:max_neighbours]

            for neighbour in nearest:
                # Avoid duplicate paths
                path1, _ = Path.objects.get_or_create(from_node=node, to_node=neighbour)
                path2, _ = Path.objects.get_or_create(from_node=neighbour, to_node=node)
                paths.extend([path1, path2])

        return paths

    def reroute_paths_around_buildings(self, paths, centre):
        """
        For any path whose straight line crosses a building footprint,
        insert a single waypoint so the rendered line visibly skirts around
        it. Paths that don't cross a footprint are left as straight lines.
        Not full pathfinding - a light heuristic, since character movement
        doesn't use these paths (visual only, issue #656).
        """
        footprints = [
            fp
            for fp in Building.objects.filter(
                population_centre=centre, footprint__isnull=False
            ).values_list("footprint", flat=True)
            if fp is not None
        ]
        if not footprints:
            return

        seen_ids = set()
        for path in paths:
            if path.pk in seen_ids:
                continue
            seen_ids.add(path.pk)

            a, c = path.from_node.location, path.to_node.location
            straight = LineString(a, c, srid=a.srid)
            blocking = next((fp for fp in footprints if fp.intersects(straight)), None)
            if blocking is None:
                continue

            waypoint = self.find_waypoint(blocking, a, c, footprints)
            if waypoint is None:
                continue

            new_geom = LineString(a, waypoint, c, srid=a.srid)
            new_length = a.distance(waypoint) + waypoint.distance(c)
            Path.objects.filter(pk=path.pk).update(geom=new_geom, length=new_length)

    def find_waypoint(self, blocking_footprint, from_point, to_point, all_footprints):
        """
        Push a waypoint away from the blocking building's centroid, starting
        just beyond its bounding radius and widening on each retry, until it
        no longer clears a line that crosses any footprint (including ones
        other than the original blocker).
        """
        minx, miny, maxx, maxy = blocking_footprint.extent
        base_radius = max(maxx - minx, maxy - miny) / 2
        mid_x = (from_point.x + to_point.x) / 2
        mid_y = (from_point.y + to_point.y) / 2

        centre_point = blocking_footprint.centroid
        away_x, away_y = mid_x - centre_point.x, mid_y - centre_point.y
        norm = math.hypot(away_x, away_y)
        if norm == 0:
            # Path runs exactly through the centroid - fall back to
            # perpendicular-to-the-path direction instead.
            dx, dy = to_point.x - from_point.x, to_point.y - from_point.y
            away_x, away_y = -dy, dx
            norm = math.hypot(away_x, away_y) or 1.0
        away_x, away_y = away_x / norm, away_y / norm

        for attempt in range(1, WAYPOINT_ATTEMPTS + 1):
            radius = base_radius + WAYPOINT_MARGIN * attempt
            waypoint = Point(
                mid_x + away_x * radius, mid_y + away_y * radius, srid=from_point.srid
            )
            leg1 = LineString(from_point, waypoint, srid=from_point.srid)
            leg2 = LineString(waypoint, to_point, srid=from_point.srid)
            if not any(
                fp.intersects(leg1) or fp.intersects(leg2) for fp in all_footprints
            ):
                return waypoint

        return None
