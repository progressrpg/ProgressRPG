import math
import random

from django.contrib.gis.geos import Point, Polygon
from django.core.management.base import BaseCommand
from django.db import transaction
from economy.constants import (
    BREAD_PER_CHARACTER_DAILY_CONSUMPTION,
    FLOUR_TO_BREAD_RATIO,
    WHEAT_TO_FLOUR_RATIO,
    YIELD_PER_AREA,
)
from locations.models import Building, LandArea, Subzone, PopulationCentre
from locations.utils import perturb_quad_corners

PLACEMENT_ATTEMPTS = 100
LANDAREA_BUFFER = 5
MIN_MARGIN_BEYOND_BOUNDARY = 10
MAX_MARGIN_BEYOND_BOUNDARY = 40

# Same jitter magnitude used for building footprints (generate_villages.py's
# create_building_footprint irregularity param) - reused as-is for v1 rather
# than tuning a separate constant, per issue #656.
FIELD_IRREGULARITY = 0.15

# A farm's crops allocation is split into a handful of separate plots
# (rather than one big rectangle) so a single farm can visually read as
# multiple fields - fixed small range for current village sizes, not scaled
# by population/area.
CROPS_PLOTS_MIN = 2
CROPS_PLOTS_MAX = 3

DAYS_PER_YEAR = 365

# Fraction of a LandArea given over to the "crops" Subzone - must match
# subdivide_landarea's own breakdown, since estimate_required_land works
# backwards from "how much crop area is needed" to "how big must the whole
# LandArea be" through this same fraction.
CROPS_SUBZONE_FRACTION = 0.60

# Wheat only grows once per year (see SOWING_WINDOW_MONTHS/GROWTH_DURATION
# in economy/constants.py - sown in spring, ready ~5 months later), so a
# single YIELD_PER_AREA harvest must cover a full year of consumption.
HARVESTS_PER_YEAR = 1


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
        Estimate required land in hectares for a village population, derived
        from the actual economy constants rather than a flat per-resident
        guess - so a village's crops Subzone is sized to actually grow
        enough wheat (after milling/baking losses) to feed its residents'
        bread consumption for a full year, plus a 20% buffer.
        """
        annual_bread_demand = BREAD_PER_CHARACTER_DAILY_CONSUMPTION * DAYS_PER_YEAR
        annual_wheat_needed = annual_bread_demand / (
            WHEAT_TO_FLOUR_RATIO * FLOUR_TO_BREAD_RATIO
        )
        crop_area_needed_m2 = (
            residents * annual_wheat_needed / (YIELD_PER_AREA * HARVESTS_PER_YEAR)
        )
        crop_area_needed_ha = crop_area_needed_m2 / 10000

        total_land_ha = crop_area_needed_ha / CROPS_SUBZONE_FRACTION
        return total_land_ha * 1.2

    def assign_landarea_geometry(self, landarea: LandArea, other_boundaries):
        """
        Place the LandArea just outside its village's own boundary, in a
        random direction, avoiding overlap with the village's own boundary
        and any other village's boundary - mirrors generate_fields' original
        placement so farmland never visually overlaps a settlement.
        Returns True if placed, False if no valid spot was found.
        """
        centre = landarea.population_centre
        # Guaranteed non-null: handle() skips any PopulationCentre with no
        # boundary/location before creating a LandArea for it.
        assert centre is not None
        assert centre.boundary is not None
        assert centre.location is not None
        # Convert hectares to rough meters (1 ha = 100 m x 100 m = 10,000 m^2)
        half_side = (landarea.size * 10000) ** 0.5 / 2

        min_x, min_y, max_x, max_y = centre.boundary.extent
        # Rough "radius" of the settlement from its own centre point, so the
        # LandArea lands just past the boundary edge regardless of direction.
        radius = max(
            max_x - centre.location.x,
            centre.location.x - min_x,
            max_y - centre.location.y,
            centre.location.y - min_y,
        )

        for _ in range(PLACEMENT_ATTEMPTS):
            angle = random.uniform(0, 2 * math.pi)
            margin = random.uniform(
                MIN_MARGIN_BEYOND_BOUNDARY, MAX_MARGIN_BEYOND_BOUNDARY
            )
            # The square's own half-diagonal reach must be added too - for a
            # LandArea whose side is comparable to (or bigger than) the
            # village itself, placing only its center point past the
            # boundary isn't enough; its near edge/corner would still fold
            # back across the settlement regardless of angle chosen.
            distance = radius + margin + half_side * math.sqrt(2)

            cx = centre.location.x + distance * math.cos(angle)
            cy = centre.location.y + distance * math.sin(angle)

            boundary = Polygon(
                (
                    (cx - half_side, cy - half_side),
                    (cx - half_side, cy + half_side),
                    (cx + half_side, cy + half_side),
                    (cx + half_side, cy - half_side),
                    (cx - half_side, cy - half_side),
                ),
                srid=3857,
            )
            buffered = boundary.buffer(LANDAREA_BUFFER)

            # Guarantee a visible gap from the centre's own boundary too, not
            # just other villages' - otherwise the LandArea's near edge can
            # land on top of the boundary line, making it look fused on.
            if centre.boundary.intersects(buffered):
                continue

            if any(other.intersects(buffered) for other in other_boundaries):
                continue

            landarea.boundary = boundary
            landarea.location = Point(cx, cy, srid=3857)
            landarea.save(update_fields=["boundary", "location"])
            return True

        return False

    def subdivide_landarea(self, landarea: LandArea):
        """
        Split a LandArea into Subzones proportionally. The "crops" share is
        further split into a handful of separate plots (a farm can own
        multiple field polygons - issue #656) instead of one single Subzone.
        """
        num_crop_plots = random.randint(CROPS_PLOTS_MIN, CROPS_PLOTS_MAX)
        crop_plot_fraction = CROPS_SUBZONE_FRACTION / num_crop_plots
        for i in range(num_crop_plots):
            Subzone.objects.create(
                name=f"{landarea.name} - Crops {i + 1}",
                land_area=landarea,
                usage="crops",
                size=landarea.size * crop_plot_fraction,
            )

        breakdown = {
            "grazing": 0.20,
            "mixed_crops": 0.20,
        }
        for usage, fraction in breakdown.items():
            Subzone.objects.create(
                name=f"{landarea.name} - {usage.capitalize()}",
                land_area=landarea,
                usage=usage,
                size=landarea.size * fraction,
            )

    def assign_subzone_geometry(self, landarea: LandArea):
        # Split LandArea square into vertical strips sized by each
        # subzone's own `size` fraction of the total (set in
        # subdivide_landarea) - splitting evenly by *count* instead would
        # silently give every subzone 1/3 of the area regardless of its
        # intended 60/20/20 breakdown, which is exactly the bug this fixed
        # (the crops Subzone's real geometry was a third of the land area,
        # not 60% of it, starving FieldCrop's actual yield potential).
        subzones = list(landarea.subzones.all())
        if not subzones:
            return

        assert (
            landarea.boundary is not None
        ), "assign_subzone_geometry requires assign_landarea_geometry to have run first"
        assert (
            landarea.size
        ), "assign_subzone_geometry requires a non-zero LandArea size"

        # Bounding box of landarea
        min_x, min_y, max_x, max_y = landarea.boundary.extent
        total_width = max_x - min_x
        height = max_y - min_y  # same height for all

        x_cursor = min_x
        for subzone in subzones:
            fraction = subzone.size / landarea.size
            x0 = x_cursor
            x1 = x0 + total_width * fraction

            corners = [
                (x0, min_y),
                (x0, max_y),
                (x1, max_y),
                (x1, min_y),
            ]
            corners = perturb_quad_corners(corners, x1 - x0, height, FIELD_IRREGULARITY)
            corners.append(corners[0])
            subzone.boundary = Polygon(corners, srid=3857)
            # center as location
            subzone.location = Point((x0 + x1) / 2, (min_y + max_y) / 2, srid=3857)
            subzone.save(update_fields=["boundary", "location"])
            x_cursor = x1

    # -----------------------------
    # Main logic
    # -----------------------------
    @transaction.atomic
    def handle(self, *args, **options):
        overwrite = options["overwrite"]

        # if overwrite:
        self.stdout.write("Deleting existing LandAreas and Subzones...")
        # Deleting a Subzone cascades its FieldCrop (generate_fields), but
        # nothing points back from Subzone/FieldCrop to the field_shelter
        # Building generate_fields also created alongside it - without this,
        # that Building is orphaned and a later generate_fields run collides
        # on its unique name when trying to recreate it for the new subzone.
        Building.objects.filter(building_type="field_shelter").delete()
        Subzone.objects.all().delete()
        LandArea.objects.all().delete()

        population_centres = list(PopulationCentre.objects.all())

        if not population_centres:
            self.stdout.write(self.style.WARNING("No population centres found."))
            return

        for pc in population_centres:
            residents = pc.residents.count()
            if residents <= 0:
                self.stdout.write(
                    self.style.WARNING(f"{pc.name} has no residents, skipping.")
                )
                continue

            if pc.boundary is None or pc.location is None:
                self.stdout.write(
                    self.style.WARNING(f"{pc.name} has no boundary, skipping.")
                )
                continue

            required_area = self.estimate_required_land(residents)

            landarea = LandArea.objects.create(
                name=f"Land area",
                population_centre=pc,
                size=required_area,
            )

            other_boundaries = [
                other.boundary
                for other in population_centres
                if other.id != pc.id and other.boundary is not None
            ]
            placed = self.assign_landarea_geometry(landarea, other_boundaries)
            if not placed:
                self.stdout.write(
                    self.style.WARNING(
                        f"Could not place a Land Area for {pc.name} after "
                        f"{PLACEMENT_ATTEMPTS} attempts - skipping."
                    )
                )
                landarea.delete()
                continue

            self.subdivide_landarea(landarea)

            self.assign_subzone_geometry(landarea)

            self.stdout.write(
                self.style.SUCCESS(
                    f"Generated {landarea} with {landarea.subzones.count()} subzones."
                )
            )

        self.stdout.write(self.style.SUCCESS("All land areas generated successfully."))
