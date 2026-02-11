from django.core.management.base import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    help = "Provision free subscriptions for users."

    def handle(self, *args, **options):
        from users.models import CustomUser
        from payments.services import provision_free_subscription

        with transaction.atomic():
            users = CustomUser.objects.filter(stripe_customer_id__isnull=True)
            for user in users:
                provision_free_subscription(user)
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Provisioned free subscription for {user.email}"
                    )
                )
