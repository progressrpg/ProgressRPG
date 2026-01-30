# locations/management/commands/generate_points.py

import random

from django.contrib.gis.db.models import Union
from django.contrib.gis.geos import Point
from django.core.management.base import BaseCommand
from django.db import transaction
from django.shortcuts import get_object_or_404

from locations.models import PopulationCentre, Node


class Command(BaseCommand):
    help = (
        "Generate OUTSIDE nodes and POI nodes inside a population centre walkable area."
    )

    def add_arguments(self, parser):
        parser.add_argument("--centre", type=int, help="Population centre ID")
        parser.add_argument(
            "--outside", type=int, default=40, help="Number of OUTSIDE nodes to create"
        )
        parser.add_argument(
            "--pois", type=int, default=10, help="Number of POI nodes to create"
        )
        parser.add_argument(
            "--spacing",
            type=float,
            default=6.0,
            help="Minimum spacing between generated nodes (SRID units)",
        )
        parser.add_argument(
            "--clearance",
            type=float,
            default=2.0,
            help="Building clearance buffer (SRID units)",
        )
        parser.add_argument(
            "--seed",
            type=int,
            default=None,
            help="Random seed for repeatable generation",
        )
        parser.add_argument(
            "--wipe",
            action="store_true",
            help="Delete existing OUTSIDE/POI nodes for the centre first",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options["seed"] is not None:
            random.seed(options["seed"])

        centres = PopulationCentre.objects.all()
        if options["centre"]:
            centres = centres.filter(id=options["centre"])

        for centre in centres:
            if not getattr(centre, "boundary", None):
                self.stdout.write(
                    self.style.WARNING(f"{centre} has no boundary; skipping")
                )
                continue

            if options["wipe"]:
                deleted, _ = Node.objects.filter(
                    population_centre=centre,
                    kind__in=[Node.Kind.OUTSIDE, Node.Kind.POI],
                ).delete()
                self.stdout.write(
                    f"{centre}: deleted {deleted} existing OUTSIDE/POI nodes"
                )

            walkable = self._compute_walkable_area(
                centre, clearance=options["clearance"]
            )
            if not walkable or walkable.empty:
                self.stdout.write(
                    self.style.WARNING(f"{centre}: walkable area empty; skipping")
                )
                continue

            created_outside = self._place_nodes(
                centre=centre,
                walkable=walkable,
                kind=Node.Kind.OUTSIDE,
                count=options["outside"],
                min_spacing=options["spacing"],
                name_prefix="Outside",
            )
            created_pois = self._place_nodes(
                centre=centre,
                walkable=walkable,
                kind=Node.Kind.POI,
                count=options["pois"],
                min_spacing=options["spacing"],
                name_prefix="POI",
            )

            self.stdout.write(
                self.style.SUCCESS(
                    f"{centre}: created {len(created_outside)} OUTSIDE nodes and {len(created_pois)} POIs"
                )
            )

    def _compute_walkable_area(self, centre, *, clearance: float):
        """
        walkable = boundary - (union(footprints).buffer(clearance))
        """
        boundary = centre.boundary

        union_geom = (
            centre.buildings.exclude(footprint__isnull=True)
            .aggregate(u=Union("footprint"))
            .get("u")
        )

        if union_geom and clearance > 0:
            union_geom = union_geom.buffer(clearance)

        walkable = boundary.difference(union_geom) if union_geom else boundary
        return walkable

    def _place_nodes(
        self,
        *,
        centre,
        walkable,
        kind,
        count: int,
        min_spacing: float,
        name_prefix: str,
        max_attempts: int = 5000,
    ):
        # If you DON'T wipe, avoid duplicating endlessly; only create missing.
        existing = Node.objects.filter(population_centre=centre, kind=kind).count()
        to_create = max(count - existing, 0)
        if to_create == 0:
            return []

        minx, miny, maxx, maxy = walkable.extent

        chosen = []
        attempts = 0
        while len(chosen) < to_create and attempts < max_attempts:
            attempts += 1
            p = Point(
                random.uniform(minx, maxx),
                random.uniform(miny, maxy),
                srid=centre.boundary.srid,
            )

            if not walkable.contains(p):
                continue

            if min_spacing > 0 and any(p.distance(q) < min_spacing for q in chosen):
                continue

            chosen.append(p)

        if len(chosen) < to_create:
            self.stdout.write(
                self.style.WARNING(
                    f"{centre}: only placed {len(chosen)}/{to_create} {kind} nodes "
                    f"(attempts={attempts}) — try reducing spacing/clearance or increase max_attempts"
                )
            )

        nodes = [
            Node(
                population_centre=centre,
                kind=kind,
                name=f"{name_prefix} {centre.id}-{i}",
                location=p,
            )
            for i, p in enumerate(chosen, start=1)
        ]
        return Node.objects.bulk_create(nodes)
