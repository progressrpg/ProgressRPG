# users/tasks.py

from celery import shared_task

# from datetime import timedelta
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone
import logging

from .models import Player
from character.models import PlayerCharacterLink

User = get_user_model()

logger = logging.getLogger("general")


@shared_task
def perform_account_wipe():
    # Get players marked for deletion
    users = User.objects.filter(pending_delete=True, delete_at__lte=timezone.now())

    for user in users:
        # Perform the actual deletion
        user.email = f"deleted_user_{user.id}"
        user.set_unusable_password()
        user.is_active = False
        user.pending_delete = False  # Clear the pending flag
        user.delete_at = None
        user.save()

        # Wipe player data
        player: Player = user.player
        player.name = f"Deleted User {user.id}"
        player.bio = ""
        player.onboarding_step = None
        player.is_premium = False
        player.total_time = 0
        player.total_activities = 0
        player.xp = 0
        player.level = 1
        player.activities.all().delete()
        player.skills.all().delete()
        player.projects.all().delete()
        player.save()

        PlayerCharacterLink.deactivate_active_links(player=player)

        player.is_deleted = True
        player.deleted_at = timezone.now()
        player.save()

        # Log the deletion
        logger.info(f"User {user.username} (ID: {user.id}) was deleted after 14 days.")


@shared_task(bind=True, retry_backoff=True, max_retries=3)
def send_email_to_users_task(
    self, emails: list, subject: str, template_base, context, cc_admin: bool
):
    """
    Celery task to send emails asynchronously.
    """
    try:
        from_email = settings.DEFAULT_FROM_EMAIL
        admin_email = "admin@progressrpg.com"

        # Add admin to CC if needed
        if cc_admin:
            emails.append(admin_email)

        plain_message = render_to_string(f"{template_base}.txt", context or {})
        html_message = render_to_string(f"{template_base}.html", context or {})

        logger.info(f"[ASYNC SEND EMAIL] Sending '{subject}' to: {emails}")

        email = EmailMultiAlternatives(
            subject,
            plain_message,
            from_email,
            emails,
        )
        email.attach_alternative(html_message, "text/html")
        email.send()

    except Exception as exc:
        logger.error(f"[ASYNC SEND EMAIL] Failed: {exc}")
        raise self.retry(exc=exc)
