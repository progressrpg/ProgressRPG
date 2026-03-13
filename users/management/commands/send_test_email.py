from django.core.management.base import BaseCommand
from django.core.mail import send_mail


class Command(BaseCommand):
    help = "Send a test email"

    def handle(self, *args, **options):

        send_mail(
            "Test",
            "Hello",
            "noreply@progressrpg.com",
            ["gaidheal01@gmail.com"],
            fail_silently=False,
        )

        self.stdout.write(self.style.SUCCESS(f"Test email sent to '{recipient}'."))
