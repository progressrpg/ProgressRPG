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


def _send_email_message(
    *,
    subject,
    plain_message,
    from_email,
    recipient_list,
    html_message="",
    headers=None,
):
    email = EmailMultiAlternatives(
        subject,
        plain_message,
        from_email,
        recipient_list,
        headers=headers,
    )

    if html_message:
        email.attach_alternative(html_message, "text/html")

    email.send()


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
        user.last_login = None
        user.save()

        # Wipe player data
        player: Player = user.player
        player.name = f"Deleted User {user.id}"
        player.bio = ""
        player.onboarding_step = 0
        player.xp = 0
        player.level = 1
        player.last_seen = None
        player.active_connections = 0
        user.logins.all().delete()
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
def send_email_to_users_task(self, emails, subject, template_base, context, cc_admin):
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

        _send_email_message(
            subject=subject,
            plain_message=plain_message,
            from_email=from_email,
            recipient_list=emails,
            html_message=html_message,
        )

    except Exception as exc:
        logger.error(f"[ASYNC SEND EMAIL] Failed: {exc}")
        raise self.retry(exc=exc)


@shared_task(bind=True, retry_backoff=True, max_retries=3)
def send_rendered_email_task(
    self,
    recipient_list,
    subject,
    plain_message,
    html_message="",
    from_email="",
    headers=None,
):
    """
    Celery task to send an already-rendered email asynchronously.
    """
    try:
        delivery_from = from_email or settings.DEFAULT_FROM_EMAIL

        logger.info(
            f"[ASYNC SEND RENDERED EMAIL] Sending '{subject}' to: {recipient_list}"
        )

        _send_email_message(
            subject=subject,
            plain_message=plain_message,
            from_email=delivery_from,
            recipient_list=recipient_list,
            html_message=html_message,
            headers=headers,
        )

    except Exception as exc:
        logger.error(f"[ASYNC SEND RENDERED EMAIL] Failed: {exc}")
        raise self.retry(exc=exc)
