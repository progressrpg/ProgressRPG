# locations/management/commands/generate_nodes.py
# locations/management/commands/generate_paths.py

from django.contrib.gis.db.models.functions import Distance
from django.core.management.base import BaseCommand
from django.db import transaction
from django.shortcuts import get_object_or_404

from locations.models import PopulationCentre, Node, Path
from locations.utils import create_hub_and_spoke


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
