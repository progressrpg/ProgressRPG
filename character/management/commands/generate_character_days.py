from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Generate character days for all characters"

    def handle(self, *args, **options):
        self.stdout.write("Generating character days for all characters...")
        self.stdout.write(
            self.style.WARNING("Character day generation is currently disabled.")
        )
        # try:
        #     with transaction.atomic():
        #         generate_character_days()
        #     self.stdout.write(
        #         self.style.SUCCESS("Character days generated successfully.")
        #     )
        # except Exception as e:
        #     self.stderr.write(self.style.ERROR(f"Error generating character days: {e}"))
