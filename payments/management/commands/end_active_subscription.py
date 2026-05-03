import logging

import stripe
from django.core.management.base import BaseCommand, CommandError

from payments.services import end_active_subscription
from users.models import CustomUser

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "End a user's active premium subscription. Pass one or more user emails."

    def add_arguments(self, parser):
        parser.add_argument(
            "emails",
            nargs="+",
            type=str,
            help="Email address(es) of the user(s) to downgrade.",
        )

    def handle(self, *args, **options):
        success_count = 0
        error_count = 0

        for email in options["emails"]:
            try:
                user = CustomUser.objects.get(email=email)
            except CustomUser.DoesNotExist:
                self.stderr.write(self.style.ERROR(f"User not found: {email}"))
                error_count += 1
                continue

            try:
                result = end_active_subscription(user)
            except stripe.error.StripeError as exc:
                self.stderr.write(self.style.ERROR(f"Stripe error for {email}: {exc}"))
                logger.error("Stripe error when downgrading %s: %s", email, exc)
                error_count += 1
                continue
            except Exception as exc:
                self.stderr.write(
                    self.style.ERROR(f"Failed to downgrade {email}: {exc}")
                )
                logger.exception("Unexpected error when downgrading %s: %s", email, exc)
                error_count += 1
                continue

            if result is None:
                self.stdout.write(
                    f"No active subscription found for {email} — skipped."
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Ended active subscription for {email} (subscription: {result.stripe_subscription_id})."
                    )
                )
                success_count += 1

        if error_count:
            raise CommandError(
                f"Completed with {success_count} success(es) and {error_count} error(s)."
            )
        self.stdout.write(
            self.style.SUCCESS(
                f"Done. Ended subscriptions for {success_count} user(s)."
            )
        )
