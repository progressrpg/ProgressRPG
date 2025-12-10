from django.contrib.gis.geos import Point, Polygon
from django.core.management.base import BaseCommand
from django.db import transaction
from locations.models import LandArea, Subzone, PopulationCentre


class Command(BaseCommand):
    help = "Generate LandAreas and Subzones for each village based on population."

    def add_arguments(self, parser):
        parser.add_argument(
            "--overwrite",
            action="store_true",
            help="Delete all existing LandAreas/Subzones before generation.",
        )

    # -----------------------------
    # Helpers
    # -----------------------------
    def estimate_required_land(self, residents: int) -> float:
        """
        Estimate required land in hectares for a village population.
        0.1 ha per resident + 20% buffer.
        """
        base = residents * 0.1
        return base * 1.2

    def assign_landarea_geometry(self, landarea: LandArea):
        # Simple square around village centre
        if landarea.population_centre and landarea.population_centre.location:
            cx, cy = (
                landarea.population_centre.location.x,
                landarea.population_centre.location.y,
            )
        else:
            cx, cy = 0, 0
        # Convert hectares to rough meters (1 ha = 100 m × 100 m = 1 ha = 10,000 m²)
        side_m = (landarea.size * 10000) ** 0.5 / 2  # half-side
        landarea.boundary = Polygon(
            (
                (cx - side_m, cy - side_m),
                (cx - side_m, cy + side_m),
                (cx + side_m, cy + side_m),
                (cx + side_m, cy - side_m),
                (cx - side_m, cy - side_m),
            )
        )
        # Use center point as location
        landarea.location = Point(cx, cy, srid=3857)
        landarea.save(update_fields=["boundary", "location"])

    def subdivide_landarea(self, landarea: LandArea):
        """
        Split a LandArea into Subzones proportionally.
        """
        breakdown = {
            "crops": 0.60,
            "grazing": 0.20,
            "mixed_crops": 0.20,
        }

        for usage, fraction in breakdown.items():
            Subzone.objects.create(
                land_area=landarea, usage=usage, size=landarea.size * fraction
            )

    def assign_subzone_geometry(self, landarea: LandArea):
        # Simplified: split LandArea square into N subzone squares
        N = len(landarea.subzones.all())
        if N == 0:
            return

        # Bounding box of landarea
        min_x, min_y, max_x, max_y = landarea.boundary.extent
        width = (max_x - min_x) / N
        height = max_y - min_y  # same height for all

        for i, subzone in enumerate(landarea.subzones.all()):
            x0 = min_x + i * width
            x1 = x0 + width
            subzone.boundary = Polygon(
                (
                    (x0, min_y),
                    (x0, max_y),
                    (x1, max_y),
                    (x1, min_y),
                    (x0, min_y),
                )
            )
            # center as location
            subzone.location = Point((x0 + x1) / 2, (min_y + max_y) / 2, srid=3857)
            subzone.save(update_fields=["boundary", "location"])

    # -----------------------------
    # Main logic
    # -----------------------------
    @transaction.atomic
    def handle(self, *args, **options):
        overwrite = options["overwrite"]

        if overwrite:
            self.stdout.write("Deleting existing LandAreas and Subzones...")
            Subzone.objects.all().delete()
            LandArea.objects.all().delete()

        population_centres = PopulationCentre.objects.all()

        if not population_centres.exists():
            self.stdout.write(self.style.WARNING("No population centres found."))
            return

        for pc in population_centres:
            residents = pc.residents.count()
            if residents <= 0:
                self.stdout.write(
                    self.style.WARNING(f"{pc.name} has no residents, skipping.")
                )
                continue

            required_area = self.estimate_required_land(residents)

            landarea = LandArea.objects.create(
                name=f"{pc.name} Land Area",
                population_centre=pc,
                size=required_area,
            )

            self.assign_landarea_geometry(landarea)

            self.subdivide_landarea(landarea)

            self.assign_subzone_geometry(landarea)

            self.stdout.write(
                self.style.SUCCESS(
                    f"Generated {landarea} with {landarea.subzones.count()} subzones."
                )
            )

        self.stdout.write(self.style.SUCCESS("All land areas generated successfully."))
