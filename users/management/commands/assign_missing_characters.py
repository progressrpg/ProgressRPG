from django.core.management.base import BaseCommand
from users.models import Player
from users.utils import assign_character_to_player


class Command(BaseCommand):
    help = "Assign characters to any players missing one."

    def handle(self, *args, **options):
        qs = Player.objects.exclude(character_link__is_active=True).distinct()

        count = 0
        for player in qs.iterator():
            assigned = assign_character_to_player(player)
            if assigned:
                count += 1

        self.stdout.write(
            self.style.SUCCESS(f"Assigned characters for {count} players.")
        )
