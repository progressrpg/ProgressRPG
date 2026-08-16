import random
from collections import defaultdict

from django.contrib.gis.geos import Point
from django.core.management.base import BaseCommand
from django.db import transaction

from economy.models import FieldCrop
from locations.models import Building, Node, Subzone
from locations.management.commands.generate_villages import (
    compute_building_entrance_point,
    create_building_footprint,
)

# Shelter buildings are a small work-site, not the field itself - sized like
# a house (matches generate_villages' residential footprint range), not the
# crops Subzone's own (much larger) area.
SHELTER_MIN_SIZE = 10
SHELTER_MAX_SIZE = 25

PLACEMENT_ATTEMPTS = 100

# Minimum distance kept between different field shelters so they read as
# visually distinct work-sites rather than overlapping.
SHELTER_MIN_SPACING = 30
SHELTER_JITTER = 15


class Command(BaseCommand):
    help = (
        "Group each population centre's 'crops' Subzones (created by "
        "generate_landarea - run that first) around one shared field_shelter "
        "Building, and attach an economy.FieldCrop to each crops Subzone "
        "pointing at that shared shelter. Skips centres with no crops "
        "Subzones yet, and crops Subzones that already have a FieldCrop."
    )

    @transaction.atomic
    def handle(self, *args, **options):
        crop_subzones = Subzone.objects.filter(
            usage="crops", land_area__population_centre__isnull=False
        ).select_related("land_area__population_centre")

        if not crop_subzones.exists():
            self.stdout.write(
                self.style.WARNING(
                    "No crops Subzones found - run generate_landarea first."
                )
            )
            return

        subzones_by_centre = defaultdict(list)
        for subzone in crop_subzones:
            subzones_by_centre[subzone.land_area.population_centre_id].append(subzone)

        existing_shelter_points = list(
            Building.objects.filter(building_type="field_shelter").values_list(
                "location", flat=True
            )
        )

        for subzones in subzones_by_centre.values():
            centre = subzones[0].land_area.population_centre
            # Guaranteed non-null: subzones_by_centre is only populated from
            # crop_subzones, which is filtered to
            # land_area__population_centre__isnull=False above.
            assert centre is not None

            pending_subzones = [
                s
                for s in subzones
                if s.boundary is not None
                and s.location is not None
                and not FieldCrop.objects.filter(subzone=s).exists()
            ]
            skipped = len(subzones) - len(pending_subzones)
            if skipped:
                self.stdout.write(
                    f"{centre.name}: {skipped} crops Subzone(s) already have a "
                    "FieldCrop or lack geometry - skipping those"
                )

            if not pending_subzones:
                continue

            shelter = self.get_or_create_shared_shelter(
                centre, pending_subzones, existing_shelter_points
            )
            if shelter is None:
                self.stdout.write(
                    self.style.WARNING(
                        f"{centre.name}: could not place a field shelter after "
                        f"{PLACEMENT_ATTEMPTS} attempts - skipping"
                    )
                )
                continue
            existing_shelter_points.append(shelter.location)

            for subzone in pending_subzones:
                FieldCrop.objects.create(
                    subzone=subzone,
                    shelter_building=shelter,
                    stage=FieldCrop.Stage.FALLOW,
                )

            self.stdout.write(
                f"Attached {len(pending_subzones)} FieldCrop(s) sharing "
                f"{shelter.name} to {centre.name}'s crops Subzones"
            )

        self.stdout.write(self.style.SUCCESS("Fields generated successfully."))

    # ------------------------------------------------------

    def get_or_create_shared_shelter(
        self, centre, pending_subzones, existing_shelter_points
    ):
        # Reuse a field shelter already created for this centre in a prior
        # run (e.g. new crops Subzones added since) instead of creating a
        # second one.
        existing = Building.objects.filter(
            population_centre=centre, building_type="field_shelter"
        ).first()
        if existing:
            return existing

        shelter_point = self.place_shared_shelter(
            pending_subzones, centre, existing_shelter_points
        )
        if shelter_point is None:
            return None

        shelter_footprint = create_building_footprint(
            shelter_point,
            min_size=SHELTER_MIN_SIZE,
            max_size=SHELTER_MAX_SIZE,
            irregularity=0,
        )
        shelter = Building.objects.create(
            name="Field Shelter",
            building_type="field_shelter",
            location=shelter_point,
            footprint=shelter_footprint,
            population_centre=centre,
        )

        Node.objects.get_or_create(
            building=shelter,
            defaults={
                "name": f"Node for {shelter.name}",
                "location": shelter.location,
                "kind": Node.Kind.BUILDING,
            },
        )
        entrance_point = compute_building_entrance_point(
            shelter.footprint, shelter.location
        )
        Node.objects.get_or_create(
            building=shelter,
            kind=Node.Kind.BUILDING_ENTRANCE,
            defaults={
                "name": f"Entrance for {shelter.name}",
                "location": entrance_point,
            },
        )
        return shelter

    def place_shared_shelter(self, pending_subzones, centre, existing_shelter_points):
        """
        Place a shared shelter on the edge of the crops plots closest to the
        population centre (shortest commute for workers), kept a minimum
        distance from other field shelters.
        """
        # Candidate points are every crop plot boundary vertex, closest to
        # the village centre first - so the shelter lands on the side of
        # the field(s) nearest the village, not buried in the middle.
        candidate_points = sorted(
            (
                Point(x, y, srid=subzone.boundary.srid)
                for subzone in pending_subzones
                for x, y in subzone.boundary.coords[0]
            ),
            key=lambda p: p.distance(centre.location),
        )

        for base_point in candidate_points:
            for attempt in range(PLACEMENT_ATTEMPTS):
                jitter_x = (
                    random.uniform(-SHELTER_JITTER, SHELTER_JITTER) if attempt else 0
                )
                jitter_y = (
                    random.uniform(-SHELTER_JITTER, SHELTER_JITTER) if attempt else 0
                )
                candidate = Point(
                    base_point.x + jitter_x,
                    base_point.y + jitter_y,
                    srid=base_point.srid,
                )
                if all(
                    candidate.distance(p) >= SHELTER_MIN_SPACING
                    for p in existing_shelter_points
                ):
                    return candidate

        return None
