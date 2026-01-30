# locations/management/commands/generate_nodes.py

from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.db.models import Union
from django.contrib.gis.geos import Point
from django.core.management.base import BaseCommand
from django.db import transaction
from locations.models import PopulationCentre, Node, Path


class Command(BaseCommand):
    help = "Generate nodes and paths."

    def add_arguments(self, parser):
        parser.add_argument(
            "--centre",
            type=int,
            help="Generate for a single population centre ID only.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        centres = PopulationCentre.objects.all()

        if options["centre"]:
            centres = centres.filter(id=options["centre"])

        for centre in centres:
            Path.objects.filter(
                from_node__population_centre=centre,
            ).delete()
            Path.objects.filter(
                to_node__population_centre=centre,
            ).delete()

            building_nodes = list(
                Node.objects.filter(
                    building__population_centre=centre,
                    kind=Node.Kind.BUILDING_ENTRANCE,
                )
            )

            if not building_nodes:
                self.stdout.write(
                    self.style.WARNING(
                        f"No building nodes found for centre {centre.name} (ID {centre.id}) – skipping"
                    )
                )
                continue

            central_node = Node.objects.get(
                population_centre=centre,
                kind=Node.Kind.CENTRE,
            )

            paths = self.create_street_network(central_node, building_nodes)

            outside_nodes = Node.objects.filter(
                population_centre=centre,
                kind=Node.Kind.OUTSIDE,
            ).exclude(pk=central_node.pk)
            paths.extend(self.connect_outside_nodes(outside_nodes))

            for path in paths:
                path.population_centre = centre
            Path.objects.bulk_update(paths, ["population_centre"])

        self.stdout.write(
            self.style.SUCCESS("All nodes and paths generated successfully.")
        )

    def create_street_network(self, central_node, building_nodes, max_neighbours=2):
        """
        Connects building nodes to each other to create 'streets',
        while keeping connections to the central node.
        """
        paths = []
        # 1 Create hub-and-spoke connections
        for node in building_nodes:
            if node == central_node:
                continue
            path1, _ = Path.objects.get_or_create(from_node=node, to_node=central_node)
            path2, _ = Path.objects.get_or_create(from_node=central_node, to_node=node)
            paths.extend([path1, path2])

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

    def connect_outside_nodes(self, outside_nodes, max_neighbours=2):
        paths = []

        for outside_node in outside_nodes:
            neighbours = self.nearest_building_nodes(outside_node, max_neighbours)

            for building_node in neighbours:
                path1, _ = Path.objects.get_or_create(
                    from_node=outside_node,
                    to_node=building_node,
                )
                path2, _ = Path.objects.get_or_create(
                    from_node=building_node,
                    to_node=outside_node,
                )
                paths.extend([path1, path2])

        return paths

    def nearest_building_nodes(self, outside_node, max_neighbours=2):
        return (
            Node.objects.filter(
                building__population_centre=outside_node.population_centre,
                kind=Node.Kind.BUILDING_ENTRANCE,
            )
            .annotate(dist=Distance("location", outside_node.location))
            .order_by("dist")[:max_neighbours]
        )
