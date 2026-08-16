from django.core.management.base import BaseCommand
from django.contrib.gis.geos import Point
import random

from character.models import Character, CharacterLocation
from character.services import relationship_services
from locations.models import Building, Node

DEFAULT_MAX_PER_BUILDING = 5


class Command(BaseCommand):
    help = (
        "Assign existing characters to residential buildings and move them "
        "there, up to a per-building cap. Characters beyond the buildings' "
        "combined capacity are left unplaced - this fills the village to a "
        "believable density, not every character."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--max-per-building",
            type=int,
            default=DEFAULT_MAX_PER_BUILDING,
            help=f"Cap on characters per residential building (default {DEFAULT_MAX_PER_BUILDING}).",
        )
        parser.add_argument(
            "--enforce-cap",
            action="store_true",
            help=(
                "Evict residents above --max-per-building from already-overcrowded "
                "buildings (e.g. left over from a run with a different cap) before "
                "placing anyone. Evicted characters are left unhoused, not moved "
                "straight to another building."
            ),
        )

    def handle(self, *args, **options):
        buildings = list(Building.objects.filter(building_type="residential"))
        if not buildings:
            self.stdout.write(self.style.WARNING("No buildings found"))
            return

        max_per_building = options["max_per_building"]

        if options["enforce_cap"]:
            self._evict_excess_residents(buildings, max_per_building)

        characters = list(Character.objects.all())
        if not characters:
            self.stdout.write(self.style.WARNING("No characters found"))
            return

        # Count existing residents so re-running this command tops up housing
        # rather than stacking new residents on top of a prior run's.
        occupancy = {building.id: building.residents.count() for building in buildings}
        already_housed_ids = set(
            CharacterLocation.objects.filter(
                role=CharacterLocation.Role.HOME,
                is_primary=True,
                location_id__in=occupancy,
            ).values_list("character_id", flat=True)
        )
        characters = [char for char in characters if char.id not in already_housed_ids]
        random.shuffle(characters)

        # Family members prefer to end up in the same population centre as
        # each other (not necessarily the same building). Computed once up
        # front so placement doesn't re-query the relationship graph per
        # character; group_population_centre records, per family group, the
        # population centre its first-placed member landed in.
        family_groups = relationship_services.relationship_get_family_groups(characters)
        group_population_centre: dict[int, int] = {}

        for char in characters:
            available = [b for b in buildings if occupancy[b.id] < max_per_building]
            if not available:
                self.stdout.write(
                    self.style.WARNING(
                        f"All residential buildings are at capacity ({max_per_building} "
                        "each) – skipping remaining characters"
                    )
                )
                break

            group_key = family_groups[char.id]
            preferred_pc_id = group_population_centre.get(group_key)
            if preferred_pc_id is not None:
                preferred = [
                    b for b in available if b.population_centre_id == preferred_pc_id
                ]
                building = (
                    random.choice(preferred) if preferred else random.choice(available)
                )
            else:
                building = random.choice(available)

            if building.population_centre_id is not None:
                group_population_centre.setdefault(
                    group_key, building.population_centre_id
                )

            if not building.nodes.exists():
                self.stdout.write(
                    self.style.WARNING(
                        f"Building {building.id} has no nodes – skipping character placement"
                    )
                )
                continue

            if char.is_moving:
                char.journeys.filter(status="active").update(status="cancelled")

            char.assign_home(building)
            occupancy[building.id] += 1

            node = None
            rooms = list(building.interiorspaces.all())

            if rooms:
                room = random.choice(rooms)
                node = room.nodes.first()
            if not node:
                node = building.nodes.filter(kind=Node.Kind.BUILDING).first()

            if not node:
                self.stdout.write(
                    self.style.WARNING(
                        f"Building {building.id} has no usable node – skipping character placement"
                    )
                )
                continue

            char.move_to(node)

            self.stdout.write(
                f"{char.name} moved to building {building.name} (ID {building.id})"
            )

        self.stdout.write(self.style.SUCCESS("Characters have been placed"))

    def _evict_excess_residents(self, buildings, max_per_building):
        for building in buildings:
            residents = list(building.residents.all())
            excess = len(residents) - max_per_building
            if excess <= 0:
                continue

            for char in random.sample(residents, excess):
                char.population_centre = None
                char.save(update_fields=["population_centre"])
                CharacterLocation.objects.filter(
                    character=char,
                    role=CharacterLocation.Role.HOME,
                    is_primary=True,
                ).delete()
                self.stdout.write(
                    f"Evicted {char.name} from overcrowded building "
                    f"{building.name} (ID {building.id})"
                )
