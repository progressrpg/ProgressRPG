import random

from django.core.management.base import BaseCommand

from character.models import Character, CharacterLocation
from economy.services.planning_services import settlement_plan
from locations.models import Building, PopulationCentre

# Buildings assigned demand-aware worker counts from settlement_plan
# (farming via field_shelter, milling/baking via BuildingCapability) rather
# than the flat random fallback below. Granary is deliberately excluded
# from both paths - no economy tick reads workers_present(granary), so
# staffing it would just be wasted headcount.
ECONOMY_ROLE_ACTIVITIES = ("milling", "baking")

# Every other work building type (inn, market, hall, communal buildings
# without a capability, etc.) keeps the original flat, demand-blind
# assignment - kept derived from Building.BUILDING_TYPES (the single source
# of truth) so a new building type added there doesn't also need
# remembering here.
WORK_BUILDING_TYPES = [
    building_type
    for building_type, _label in Building.BUILDING_TYPES
    if building_type not in ("residential", "granary")
]
MIN_WORKING_AGE = 16
MAX_WORKING_AGE = 65
MIN_WORKERS_PER_BUILDING = 2
MAX_WORKERS_PER_BUILDING = 3


class Command(BaseCommand):
    help = (
        "Assign working-age characters to work in the village's "
        "non-residential, non-granary buildings. Farming/milling/baking "
        "buildings are staffed to meet settlement_plan's demand estimate, "
        "greedily filling one building to MAX_WORKERS_PER_BUILDING before "
        "moving to the next of the same role (so a village with too few "
        "eligible workers ends up understaffed rather than evenly thin "
        "everywhere) - a village can fall short of settlement_plan's "
        "recommendation, which is the point: this is what makes the "
        "'struggling at spawn' arc real rather than guaranteed by "
        "construction. Every other work building keeps the original flat "
        "2-3 random workers per building, since there's no demand model "
        "for those roles."
    )

    def handle(self, *args, **options):
        assigned_ids: set[int] = set()
        processed_building_ids: set[int] = set()

        for centre in PopulationCentre.objects.all():
            self.assign_economy_role_workers(
                centre, assigned_ids, processed_building_ids
            )

        self.assign_fallback_workers(assigned_ids, processed_building_ids)

        self.stdout.write(self.style.SUCCESS("Workers have been assigned"))

    # ------------------------------------------------------

    def assign_economy_role_workers(self, centre, assigned_ids, processed_building_ids):
        plan = settlement_plan(population_centre=centre)
        remaining = {
            "farming": plan.farming.workers_needed,
            "milling": plan.milling.workers_needed,
            "baking": plan.baking.workers_needed,
        }

        field_shelters = Building.objects.filter(
            population_centre=centre, building_type="field_shelter"
        ).order_by("id")
        for building in field_shelters:
            processed_building_ids.add(building.id)
            target = min(remaining["farming"], MAX_WORKERS_PER_BUILDING)
            assigned_count = self.fill_building(building, target, assigned_ids)
            remaining["farming"] -= assigned_count

        capability_buildings = (
            Building.objects.filter(
                population_centre=centre,
                capabilities__activity__in=ECONOMY_ROLE_ACTIVITIES,
            )
            .distinct()
            .order_by("id")
            .prefetch_related("capabilities")
        )
        for building in capability_buildings:
            processed_building_ids.add(building.id)
            activities = [
                capability.activity
                for capability in building.capabilities.all()
                if capability.activity in ECONOMY_ROLE_ACTIVITIES
            ]
            if not activities:
                continue

            # A present worker counts fully toward every activity their
            # building holds at once (see capacity_services.
            # worker_capacity_present, called independently per tick) - so
            # a shared (e.g. "communal") building's target is the largest
            # of its activities' remaining demand, not their sum, and
            # filling it counts against every activity it holds, not just
            # one.
            target = min(
                max(remaining[a] for a in activities), MAX_WORKERS_PER_BUILDING
            )
            assigned_count = self.fill_building(building, target, assigned_ids)
            for activity in activities:
                remaining[activity] = max(0, remaining[activity] - assigned_count)

    def fill_building(self, building, target_count, assigned_ids):
        if target_count <= 0:
            return 0
        if not building.nodes.exists():
            self.stdout.write(
                self.style.WARNING(
                    f"Building {building.id} has no nodes – skipping work assignment"
                )
            )
            return 0

        eligible = self.eligible_characters(building.population_centre, assigned_ids)
        if not eligible:
            return 0

        workers = random.sample(eligible, min(target_count, len(eligible)))
        for char in workers:
            char.assign_work(building)
            assigned_ids.add(char.id)
            self.stdout.write(
                f"{char.name} now works at {building.name} (ID {building.id})"
            )
        return len(workers)

    def eligible_characters(self, population_centre, assigned_ids):
        return [
            char
            for char in Character.objects.filter(
                population_centre=population_centre,
                locations__role=CharacterLocation.Role.HOME,
                locations__is_primary=True,
            )
            if char.id not in assigned_ids
            and MIN_WORKING_AGE <= (char.get_age() // 365) <= MAX_WORKING_AGE
        ]

    def assign_fallback_workers(self, assigned_ids, processed_building_ids):
        work_buildings = Building.objects.filter(
            building_type__in=WORK_BUILDING_TYPES
        ).exclude(id__in=processed_building_ids)

        for building in work_buildings:
            slots = random.randint(MIN_WORKERS_PER_BUILDING, MAX_WORKERS_PER_BUILDING)
            self.fill_building(building, slots, assigned_ids)
