import math
import random
from django.core.management.base import BaseCommand
from django.contrib.gis.geos import Point, Polygon, MultiPolygon
from economy.models import BuildingCapability
from economy.services.planning_services import settlement_plan
from locations.models import PopulationCentre, Building, InteriorSpace, Node, Path
from locations.services import population_estimation
from locations.utils import perturb_quad_corners, rotate_point
from locations.village_names import VILLAGE_NAMES
from math import sqrt


SPECIAL_BUILDINGS = ["granary", "inn", "mill", "bakery", "communal"]
# Which of SPECIAL_BUILDINGS get a BuildingCapability row - granary/inn/
# communal aren't labor-capped production activities (see
# economy.models.BuildingCapability's docstring); mill/bakery are, and
# without this the mill/bakery buildings this command creates would be
# invisible to capacity_services.find_mill/find_bakery, which look up
# capabilities__activity rather than building_type.
SPECIAL_BUILDING_CAPABILITIES = {
    "mill": BuildingCapability.Activity.MILLING,
    "bakery": BuildingCapability.Activity.BAKING,
}
RESIDENTIAL_PER_VILLAGE = 5
IRREGULARITY = 0
BUILDING_BUFFER = 2

# Two fixed neighbourhoods per village: "social" buildings (housing, inn,
# communal) cluster on one side, "craft"/work buildings on the other, so a
# village reads as distinct areas rather than a uniform scatter. Fixed at
# two rather than one-per-building-type to keep the placement bias simple -
# see .claude/plans/656-village-layout-generator-v2.md.
BUILDING_ZONES = {
    "residential": "social",
    "inn": "social",
    "communal": "social",
    "granary": "craft",
    "mill": "craft",
    "bakery": "craft",
}
# Distance of each zone's anchor point from the village centre. Must clear
# ZONE_BUILDING_SPREAD by a wide enough margin that the two zones' building
# clouds don't overlap - otherwise the clustering bias is too weak to be
# statistically detectable (see SpawnVillagesZoneGroupingTest).
ZONE_ANCHOR_DISTANCE = 60
# Random offset range (in each axis) for a building around its zone anchor.
ZONE_BUILDING_SPREAD = 20
# Wider fallback offset range (around the village centre, not a zone anchor)
# used only if a building can't be placed near its zone anchor after
# PLACEMENT_ATTEMPTS tries - keeps the original best-effort behaviour so a
# crowded zone doesn't cause the whole building to be skipped.
FALLBACK_BUILDING_SPREAD = 50
PLACEMENT_ATTEMPTS = 100


def distance(p1: Point, p2: Point):
    """Euclidean distance between two Points."""
    dx = p1.x - p2.x
    dy = p1.y - p2.y
    return sqrt(dx * dx + dy * dy)


def create_building_footprint(
    centre: Point, min_size=5, max_size=20, irregularity=IRREGULARITY, rotation=0.0
):
    """Return a polygon around the building location with variation."""
    if not centre:
        raise ValueError(f"create_building_footprint needs Point to exist!")

    x, y = centre.x, centre.y

    width = random.uniform(min_size, max_size)
    height = random.uniform(min_size, max_size)

    hw, hh = width / 2, height / 2

    corners = [
        (x - hw, y - hh),
        (x - hw, y + hh),
        (x + hw, y + hh),
        (x + hw, y - hh),
    ]

    corners = perturb_quad_corners(corners, width, height, irregularity)

    if rotation:
        corners = [rotate_point(cx, cy, x, y, rotation) for cx, cy in corners]

    corners.append(corners[0])

    return Polygon(corners)


def create_centre_boundary(buildings: list[Polygon], padding=10):
    """Return a polygon roughly surrounding all building footprints."""
    if not buildings:
        return None

    multi = MultiPolygon(buildings)
    hull = multi.convex_hull
    return hull.buffer(padding)


def compute_building_entrance_point(
    footprint: Polygon | None, fallback: Point
) -> Point:
    """Pick a point along the longest wall as a building entrance."""
    if not footprint:
        return fallback

    coords = list(footprint.coords[0]) if footprint.coords else []
    if len(coords) < 2:
        return fallback

    best_midpoint = None
    best_length: float = -1
    for i in range(len(coords) - 1):
        (x1, y1), (x2, y2) = coords[i], coords[i + 1]
        dx = x2 - x1
        dy = y2 - y1
        length = sqrt(dx * dx + dy * dy)
        if length > best_length:
            best_length = length
            best_midpoint = Point((x1 + x2) / 2, (y1 + y2) / 2, srid=fallback.srid)

    return best_midpoint or fallback


class Command(BaseCommand):
    help = "Spawn population centres with buildings clustered around them, with footprints and boundaries"

    def add_arguments(self, parser):
        parser.add_argument("--num-centres", type=int, default=2)
        parser.add_argument("--grid-size", type=int, default=5000)
        parser.add_argument("--min-distance", type=int, default=3)
        parser.add_argument(
            "--clear-all",
            action="store_true",
            help=(
                "Delete all existing PopulationCentres and start from "
                "scratch. Default behaviour keeps each existing centre's "
                "point and name, only regenerating its buildings/nodes/paths."
            ),
        )

    def attempt_place_centre(
        self,
        centres_positions,
        grid_size=5000,
        min_centre_distance=1000,
        max_centre_distance=2000,
    ):
        x = random.randint(0, grid_size)
        y = random.randint(0, grid_size)
        new_point = Point(x, y)

        if not centres_positions:
            return new_point

        for cp in centres_positions:
            d = distance(new_point, cp)

            if d < min_centre_distance or d > max_centre_distance:
                return False

        return new_point

    def compute_zone_anchors(self, centre_point: Point) -> dict[str, Point]:
        """
        Pick a "social" and a "craft" anchor point on opposite sides of the
        village centre, so buildings biased toward each anchor read as two
        distinct neighbourhoods rather than a uniform scatter.
        """
        angle = random.uniform(0, 2 * math.pi)
        social = Point(
            centre_point.x + ZONE_ANCHOR_DISTANCE * math.cos(angle),
            centre_point.y + ZONE_ANCHOR_DISTANCE * math.sin(angle),
        )
        craft = Point(
            centre_point.x + ZONE_ANCHOR_DISTANCE * math.cos(angle + math.pi),
            centre_point.y + ZONE_ANCHOR_DISTANCE * math.sin(angle + math.pi),
        )
        return {"social": social, "craft": craft}

    def attempt_place_building(
        self, anchor_point: Point, placed_buildings, min_distance, spread
    ):
        offset_x = random.randint(-spread, spread)
        offset_y = random.randint(-spread, spread)
        candidate = Point(anchor_point.x + offset_x, anchor_point.y + offset_y)

        if all(distance(candidate, bp) >= min_distance for bp in placed_buildings):
            return candidate

        return None

    def place_building_footprint(
        self,
        anchor_point: Point,
        spread: int,
        placed_building_points,
        placed_footprints,
        min_distance,
    ):
        """
        Try up to PLACEMENT_ATTEMPTS times to find a non-overlapping spot for
        a building near anchor_point. Returns (point, footprint) or
        (None, None) if no spot was found.
        """
        for _ in range(PLACEMENT_ATTEMPTS):
            building_point = self.attempt_place_building(
                anchor_point, placed_building_points, min_distance, spread
            )
            if building_point is None:
                continue

            footprint = create_building_footprint(
                building_point,
                min_size=10,
                max_size=25,
                irregularity=0,
                rotation=random.uniform(0, 360),
            )
            buffered_footprint = footprint.buffer(BUILDING_BUFFER)
            if all(
                not buffered_footprint.intersects(existing_fp.buffer(BUILDING_BUFFER))
                for existing_fp in placed_footprints
            ):
                return building_point, footprint

        return None, None

    def handle(self, *args, **options):
        num_centres = options["num_centres"]
        grid_size = options["grid_size"]
        min_distance = options["min_distance"]
        clear_all = options["clear_all"]

        if clear_all:
            PopulationCentre.objects.all().delete()
            Building.objects.all().delete()
            InteriorSpace.objects.all().delete()
            Node.objects.all().delete()
            Path.objects.all().delete()
            self.stdout.write("Deleted all existing game world locations")
            existing_centres: list[PopulationCentre] = []
        else:
            # Reuse each existing centre's point/name rather than randomising
            # a new one every run - only the centres we're about to
            # regenerate (up to num_centres) get their contents cleared;
            # any existing centres beyond that are left untouched entirely.
            existing_centres = list(PopulationCentre.objects.all()[:num_centres])
            if existing_centres:
                Building.objects.filter(population_centre__in=existing_centres).delete()
                # Building.delete() cascades its own Nodes/InteriorSpaces;
                # this catches the centre-level CENTRE/OUTSIDE/POI nodes.
                Node.objects.filter(population_centre__in=existing_centres).delete()
                Path.objects.filter(population_centre__in=existing_centres).delete()
                self.stdout.write(
                    f"Keeping {len(existing_centres)} existing centre(s); "
                    "regenerating their buildings/nodes/paths"
                )

        centres_positions: list[Point] = [c.location for c in existing_centres]
        # Place centres
        for i in range(num_centres):
            existing_centre = existing_centres[i] if i < len(existing_centres) else None
            if existing_centre:
                new_point = existing_centre.location
                centre_name = existing_centre.name
            else:
                for attempt in range(100):
                    result = self.attempt_place_centre(
                        centres_positions,
                        grid_size=5000,
                        min_centre_distance=1000,
                        max_centre_distance=2000,
                    )
                    if result:
                        new_point = result
                        break
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Could not place centre {i+1} after 100 attempts"
                        )
                    )
                    continue
                centre_name = f"{random.choice(VILLAGE_NAMES)} village"

            # Place buildings around this centre
            residential_buildings = [
                f"residential-{i+1}" for i in range(RESIDENTIAL_PER_VILLAGE)
            ]
            all_buildings_to_place = SPECIAL_BUILDINGS + residential_buildings
            zone_anchors = self.compute_zone_anchors(new_point)

            placed_building_points: list[Point] = []
            placed_footprints: list[Polygon] = []
            created_buildings = []
            for btype_or_name in all_buildings_to_place:
                if btype_or_name in SPECIAL_BUILDINGS:
                    building_name = f"{btype_or_name.capitalize()}"
                    building_type = btype_or_name
                else:
                    building_name = f"House {btype_or_name.split('-')[1]}"
                    building_type = "residential"

                zone_anchor = zone_anchors[BUILDING_ZONES.get(building_type, "social")]

                building_point, footprint = self.place_building_footprint(
                    zone_anchor,
                    ZONE_BUILDING_SPREAD,
                    placed_building_points,
                    placed_footprints,
                    min_distance,
                )
                if building_point is None:
                    # Zone anchor is too crowded - fall back to the original
                    # wider search around the village centre before skipping.
                    building_point, footprint = self.place_building_footprint(
                        new_point,
                        FALLBACK_BUILDING_SPREAD,
                        placed_building_points,
                        placed_footprints,
                        min_distance,
                    )

                if building_point is None:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Could not place building {btype_or_name} in {centre_name} after "
                            f"{PLACEMENT_ATTEMPTS} attempts"
                        )
                    )
                    continue

                placed_footprints.append(footprint)
                building = Building.objects.create(
                    name=building_name,
                    building_type=building_type,
                    location=building_point,
                    footprint=footprint,
                    population_centre=None,
                )
                activity = SPECIAL_BUILDING_CAPABILITIES.get(building_type)
                if activity:
                    BuildingCapability.objects.create(
                        building=building, activity=activity
                    )

                placed_building_points.append(building_point)
                created_buildings.append(building)
                self.stdout.write(f"  Placed {building_name} at {building_point}")

            boundary = create_centre_boundary(placed_footprints)

            if existing_centre:
                existing_centre.boundary = boundary
                existing_centre.save(update_fields=["boundary"])
                centre = existing_centre
            else:
                centre = PopulationCentre.objects.create(
                    name=centre_name, location=new_point, boundary=boundary
                )

            Node.objects.get_or_create(
                name=f"Central node of settlement {centre.name}",
                population_centre=centre,
                defaults={
                    "location": centre.location,
                    "kind": Node.Kind.CENTRE,
                },
            )

            Building.objects.filter(pk__in=[b.pk for b in created_buildings]).update(
                population_centre=centre
            )

            for building in created_buildings:
                Node.objects.get_or_create(
                    building=building,
                    defaults={
                        "name": f"Node for {building.name}",
                        "location": building.location,
                        "kind": Node.Kind.BUILDING,
                    },
                )
                if building.building_type != "granary":
                    entrance_point = compute_building_entrance_point(
                        building.footprint, building.location
                    )
                    Node.objects.get_or_create(
                        building=building,
                        kind=Node.Kind.BUILDING_ENTRANCE,
                        defaults={
                            "name": f"Entrance for {building.name}",
                            "location": entrance_point,
                        },
                    )

            # Compute-and-log only for now (see population_estimation's
            # module docstring and
            # .claude/plans/village-capacity-sizing-plan.md step 3) - this
            # doesn't yet change which buildings get created. It's here to
            # validate the recommended plan against real generated villages
            # before generation behaviour changes in a later step.
            estimated_population = population_estimation.starting_population(centre)
            recommended_plan = settlement_plan(population=estimated_population)
            self.stdout.write(
                f"  Estimated starting population {estimated_population} -> "
                f"recommended plan (granaries={recommended_plan.recommended_granaries}, "
                f"milling buildings={recommended_plan.milling.recommended_buildings}, "
                f"baking buildings={recommended_plan.baking.recommended_buildings}, "
                f"farming buildings={recommended_plan.farming.recommended_buildings})"
            )

            if not existing_centre:
                centres_positions.append(new_point)
            verb = "Updated" if existing_centre else "Created"
            self.stdout.write(f"{verb} PopulationCentre: {centre_name} at {new_point}")

        self.stdout.write(
            self.style.SUCCESS("Finished spawning population centres with buildings")
        )
