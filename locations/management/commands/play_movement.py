from django.core.management.base import BaseCommand
from locations.models import Position, Movable
from character.models import Character
import random


class Command(BaseCommand):
    help = "Spawn test characters and move them around"

    def handle(self, *args, **options):
        # Create 5 test characters if they don't exist
        characters = []
        for i in range(5):
            name = f"TestChar{i+1}"
            char, created = Character.objects.get_or_create(
                name=name,
                defaults={"movement_speed": random.uniform(1.0, 2.0)},
            )
            characters.append(char)
            if created:
                self.stdout.write(f"Created character: {name} at {char.position}")

        # Move each character to a random position
        for char in characters:
            new_pos = Position.objects.create(
                x=random.randint(0, 10), y=random.randint(0, 10)
            )
            travel_time = char.move_to(new_pos)
            self.stdout.write(
                f"{char.name} moved to {char.position} in {travel_time:.2f} units of time."
            )

        # Show pairwise distances
        self.stdout.write("\nDistances between characters:")
        for i in range(len(characters)):
            for j in range(i + 1, len(characters)):
                d = characters[i].position.calculate_distance(characters[j].position)
                self.stdout.write(
                    f"{characters[i].name} <-> {characters[j].name}: {d:.2f}"
                )
