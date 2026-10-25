# locations/management/commands/generate_characters.py

import random
import math
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point
from django.core.management.base import BaseCommand
from django.db import transaction
from datetime import date, timedelta
from locations.constants import PROJECT_SRID
from locations.models import PopulationCentre, Node, Path, Building
from locations.services import population_estimation
from character.models import Character, PlayerCharacterLink
from character.services import household_services

MALE_NAMES = [
    "Gareth",
    "Tristan",
    "Oswin",
    "Callum",
    "Ronan",
    "Nico",
    "Aldwin",
    "Edric",
    "Elias",
    "Viggo",
    "Marwen",
    "Theo",
    "Dain",
    "Baldric",
    "Aelfric",
    "Aethelred",
    "Aethelwin",
    "Beorn",
    "Beric",
    "Cedric",
    "Cuthbert",
    "Eadgar",
    "Eadmund",
    "Ealdred",
    "Godric",
    "Hereward",
    "Leofric",
    "Osbert",
    "Osmund",
    "Roderic",
    "Sigeric",
    "Thurstan",
    "Wulfric",
    "Wynfrid",
]

FEMALE_NAMES = [
    "Agnes",
    "Mira",
    "Anwen",
    "Elena",
    "Ivy",
    "Ysabet",
    "Rowenna",
    "Loralei",
    "Eda",
    "Rosalind",
    "Freya",
    "Ella",
    "Sylvie",
    "Thea",
    "Aelfgifu",
    "Aethelwyn",
    "Edith",
    "Eadgyth",
    "Elfrida",
    "Godgifu",
    "Hilda",
    "Leofgifu",
    "Mildred",
    "Osburga",
    "Sibyl",
    "Wynflaed",
    "Eadwina",
    "Isolde",
    "Maud",
]


def birth_date_for_age(age_years: int):
    today = date.today()

    # Add fuzz: random extra days in the year, so a whole household doesn't
    # land on suspiciously round ages.
    extra_days = random.randint(0, 364)

    return today - timedelta(days=age_years * 365 + extra_days)


class Command(BaseCommand):
    help = "Generate characters for each village based on residential capacity."

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

        self.stdout.write("Deleting existing unlinked characters…")

        linked_ids = PlayerCharacterLink.objects.values_list("character_id", flat=True)
        Character.objects.exclude(id__in=linked_ids).delete()

        for centre in centres:
            self.generate_for_centre(centre)

        # Place linked characters
        id_list = list(linked_ids)
        buildings = Building.objects.all()
        chars = Character.objects.all()
        for char in chars:
            if char.id in id_list:
                building = random.choice(buildings)
                char.assign_home(building)
                node = building.nodes.first()
                if node is not None:
                    char.move_to(node)

    def generate_for_centre(self, centre: PopulationCentre):
        buildings = list(centre.buildings.filter(building_type="residential"))
        building_count = len(buildings)

        num_chars = population_estimation.starting_population(centre)

        self.stdout.write(
            f"{centre.name}: Buildings={building_count}, Generating {num_chars} characters..."
        )

        # Generate whole household units (family/single-adult/roommates -
        # see household_services) rather than num_chars independent
        # characters, so ages and relationships (MARRIAGE/PARENT_CHILD) come
        # out coherent instead of being assigned independently and hoping
        # they happen to form plausible families.
        households = []
        remaining = num_chars
        while remaining > 0:
            household = household_services.household_member_ages(remaining)
            household_members = []
            household_characters = []
            for age, role in household:
                sex = random.choice(["M", "F"])
                given_name = random.choice(MALE_NAMES if sex == "M" else FEMALE_NAMES)

                birth_date = birth_date_for_age(age)

                char = Character.objects.create(
                    given_name=given_name,
                    sex=sex,
                    birth_date=birth_date,
                )
                household_members.append((char, role))
                household_characters.append(char)

            household_services.create_household_relationships(household_members)
            households.append(household_characters)
            remaining -= len(household)

        self._assign_households_to_buildings(households, buildings)

    def _assign_households_to_buildings(self, households, buildings):
        """
        Try to keep each household together in a single building, weighted
        by each building's own residential_capacity (not a uniform
        random.choice() - see the regression this guards against in
        test_no_building_exceeds_its_own_capacity). A household that can't
        fit whole into any building with remaining room (occupancy-factored
        capacities are often smaller than a large family) spills its
        members individually across whatever capacity is left, rather than
        leaving the whole household unhoused over one building being full.
        """
        remaining_capacity = {
            building: population_estimation.residential_capacity(building)
            for building in buildings
        }
        order = list(buildings)
        random.shuffle(order)

        for household in households:
            size = len(household)
            fitting = [b for b in order if remaining_capacity[b] >= size]
            if fitting:
                building = random.choice(fitting)
                remaining_capacity[building] -= size
                for char in household:
                    self._house_character(char, building)
                continue

            members = iter(household)
            char = next(members, None)
            for building in order:
                while char is not None and remaining_capacity[building] > 0:
                    self._house_character(char, building)
                    remaining_capacity[building] -= 1
                    char = next(members, None)
                if char is None:
                    break
            # Any characters left over here mean the centre's combined
            # capacity is exhausted - they simply stay unhoused (Character
            # has no building), same as an empty buildings list already did.

    def _house_character(self, char, building):
        char.assign_home(building)
        node = building.nodes.first()
        if node is not None:
            char.move_to(node)
        char.save()

    def generate_nodes(self, pop_centre: PopulationCentre, buildings, num: int):
        outside_nodes = []
        building_footprints = [b.footprint for b in buildings if b.footprint]

        for i in range(num):
            for attempt in range(50):  # try a few times to avoid collisions
                # pick a random offset from village centre
                angle = random.random() * 2 * math.pi
                r = random.random() * 100  # adjust radius as needed
                x = pop_centre.location.x + math.cos(angle) * r
                y = pop_centre.location.y + math.sin(angle) * r
                point = Point(x, y, srid=PROJECT_SRID)

                # make sure it doesn’t overlap a building
                if any(fp.contains(point) for fp in building_footprints):
                    continue

                node = Node.objects.create(
                    name=f"Outside node {i+1} for ({pop_centre.name})",
                    location=point,
                    kind=Node.Kind.OUTSIDE,
                    population_centre=pop_centre,
                )
                outside_nodes.append(node)
                break

        return outside_nodes

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
                population_centre=outside_node.population_centre,
                building__isnull=False,
            )
            .annotate(dist=Distance("location", outside_node.location))
            .order_by("dist")[:max_neighbours]
        )
