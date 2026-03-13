import json
from django.core.management.base import BaseCommand
from django.utils.dateparse import parse_date
from character.models import Character


class Command(BaseCommand):
    help = "Import birth_date from seed_data.json fixture"

    def handle(self, *args, **options):
        with open("seed_data.json") as f:
            data = json.load(f)

        updated = 0

        for obj in data:
            if obj["model"] != "character.character":
                continue

            pk = obj["pk"]
            fields = obj["fields"]

            birth_date = fields.get("birth_date")

            if not birth_date:
                continue

            try:
                char = Character.objects.get(pk=pk)
                char.birth_date = parse_date(birth_date)
                char.save(update_fields=["birth_date"])
                updated += 1

            except Character.DoesNotExist:
                print(f"Missing character pk={pk}")

        print(f"Updated {updated} characters")
