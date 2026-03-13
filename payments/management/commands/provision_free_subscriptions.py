from django.core.management.base import BaseCommand

from payments.services import provision_free_subscription
from users.models import CustomUser


class Command(BaseCommand):
    help = "Provision free Stripe subscriptions for users without one."

    def handle(self, *args, **options):
        count = 0
        users = CustomUser.objects.select_related("player").all()

        for user in users:
            try:
                provision_free_subscription(user)
                count += 1
            except Exception as exc:
                self.stderr.write(f"Failed for user {user.id}: {exc}")

        self.stdout.write(
            self.style.SUCCESS(f"Provisioned free subscriptions for {count} users.")
        )
