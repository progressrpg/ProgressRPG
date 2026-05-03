from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Deprecated: free Stripe subscription provisioning has been removed."

    def handle(self, *args, **options):
        raise CommandError(
            "Free Stripe subscription provisioning has been removed. "
            "Free users are not created in Stripe until they start a premium checkout session."
        )
