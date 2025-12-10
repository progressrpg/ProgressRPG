# locations/management/commands/generate_characters.py

import random
from django.core.management.base import BaseCommand
from django.db import transaction
from datetime import date, timedelta
from locations.models import PopulationCentre
from character.models import Character, PlayerCharacterLink

CHARS_PER_BUILDING = 5

MALE_NAMES = [
    "Elrond",
    "Gareth",
    "Tristan",
    "Oswin",
    "Callum",
    "Ronan",
    "Ronan",
    "Nico",
    "Aldwin",
    "Edric",
    "Elias",
    "Viggo",
    "Dain",
    "Marwen",
    "Theo",
    "Dain",
    "Baldric",
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
        buildings = list(centre.buildings.all())
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
