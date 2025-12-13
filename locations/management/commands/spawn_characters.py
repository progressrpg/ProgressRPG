# locations/management/commands/generate_characters.py

import random
import math
from django.contrib.gis.db.models.functions import Distance
from django.core.management.base import BaseCommand
from django.db import transaction
from datetime import date, timedelta
from locations.models import PopulationCentre, Point, Node, Path
from character.models import Character, PlayerCharacterLink


CHARS_PER_BUILDING = 5

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

LAST_NAMES = [
    "Drake",
    "Dewhurst",
    "Ironhand",
    "Weaver",
    "Blackthorne",
    "Lockwood",
    "Brightwater",
    "Fenwick",
    "Thornbrook",
    "Stormvale",
    "Holt",
    "Briarwood",
    "Holloway",
    "Ashford",
    "Mossgrove",
    "Atwood",
    "Baker",
    "Brook",
    "Cartwright",
    "Clayton",
    "Cooper",
    "Crowhurst",
    "Fielding",
    "Fletcher",
    "Greenhill",
    "Hardwick",
    "Millward",
    "Shepherd",
    "Stonebridge",
    "Tanner",
    "Underhill",
    "Webster",
    "Whiteoak",
]


def random_birth_date():
    today = date.today()

    # Give age between 0 and 90
    age_years = int(random.triangular(0, 90, 25))
    # triangular(min, max, mode) → mode makes age cluster around 25

    # Add fuzz: random extra days in the year
    extra_days = random.randint(0, 364)

    # Convert “age in years” + extra days into a date
    return today - timedelta(days=age_years * 365 + extra_days)


class Command(BaseCommand):
    help = "Generate characters for each village based on building count."

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

    def generate_for_centre(self, centre: PopulationCentre):
        buildings = list(centre.buildings.filter(building_type="residential"))
        building_count = len(buildings)

        num_chars = int(building_count * CHARS_PER_BUILDING * random.uniform(0.8, 1.2))

        self.stdout.write(
            f"{centre.name}: Buildings={building_count}, Generating {num_chars} characters..."
        )

        characters = []
        for _ in range(num_chars):
            building = random.choice(buildings)

            sex = random.choice(["M", "F"])
            first_name = random.choice(MALE_NAMES if sex == "M" else FEMALE_NAMES)
            last_name = random.choice(LAST_NAMES)

            birth_date = random_birth_date()
            # can_link possible for chars over 15 years old
            age_days = (date.today() - birth_date).days
            can_link = age_days >= int(15 * 365.25)

            characters.append(
                Character(
                    first_name=first_name,
                    last_name=last_name,
                    name=f"{first_name} {last_name}",
                    sex=sex,
                    birth_date=birth_date,
                    can_link=can_link,
                    building=building,
                    population_centre=centre,
                )
            )

        Character.objects.bulk_create(characters)

        outside_nodes = self.generate_nodes(centre, buildings, num_chars)

        paths = self.connect_outside_nodes(outside_nodes)

    def generate_nodes(self, pop_centre, buildings, num):
        outside_nodes = []
        building_footprints = [b.footprint for b in buildings if b.footprint]

        for i in range(num):
            for attempt in range(50):  # try a few times to avoid collisions
                # pick a random offset from village centre
                angle = random.random() * 2 * math.pi
                r = random.random() * 100  # adjust radius as needed
                x = pop_centre.location.x + math.cos(angle) * r
                y = pop_centre.location.y + math.sin(angle) * r
                point = Point(x, y, srid=pop_centre.location.srid)

                # make sure it doesn’t overlap a building
                if any(fp.contains(point) for fp in building_footprints):
                    continue

                node = Node.objects.create(
                    name=f"Outside node {i+1} for ({pop_centre.name})",
                    location=point,
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
