from django.core.management.base import BaseCommand

from character.models import CharacterLocation
from locations.models import Node


class Command(BaseCommand):
    help = (
        "Force one or all characters to walk to their home or work location "
        "right now, bypassing the normal time-of-day schedule. Useful for "
        "manually testing the commute movement stack without waiting for or "
        "faking the clock - just run the command and watch the map (needs "
        "the celery worker running, since it drives the actual walk)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--role",
            choices=[CharacterLocation.Role.HOME, CharacterLocation.Role.WORK],
            required=True,
            help="Which location to send characters to.",
        )
        parser.add_argument(
            "--character",
            type=int,
            help=(
                "Only move this character (by id). Defaults to every "
                "character with a matching primary CharacterLocation."
            ),
        )

    def handle(self, *args, **options):
        role = options["role"]
        character_id = options.get("character")

        locations = CharacterLocation.objects.filter(
            role=role, is_primary=True
        ).select_related("character", "location")
        if character_id:
            locations = locations.filter(character_id=character_id)

        if not locations.exists():
            self.stdout.write(
                self.style.WARNING(f"No characters have a primary {role} location")
            )
            return

        moved = 0
        for loc in locations:
            char = loc.character

            if char.is_moving:
                self.stdout.write(f"{char.name} is already moving - skipping")
                continue

            entrance_node = Node.objects.filter(
                building=loc.location, kind=Node.Kind.BUILDING_ENTRANCE
            ).first()
            if not entrance_node:
                self.stdout.write(
                    self.style.WARNING(
                        f"{loc.location} has no entrance node - skipping {char.name}"
                    )
                )
                continue

            if char.current_node_id == entrance_node.id:
                self.stdout.write(f"{char.name} is already at {loc.location}")
                continue

            try:
                char.set_destination(node=entrance_node)
            except ValueError as exc:
                self.stdout.write(
                    self.style.WARNING(
                        f"Could not route {char.name} to {loc.location}: {exc}"
                    )
                )
                continue

            moved += 1
            self.stdout.write(f"{char.name} is heading to {loc.location} ({role})")

        self.stdout.write(self.style.SUCCESS(f"Started {moved} journey(s)"))
