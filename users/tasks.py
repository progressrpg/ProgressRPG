# users/tasks.py

from asgiref.sync import async_to_sync
from celery import shared_task
from channels.layers import get_channel_layer

from datetime import timedelta
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import EmailMultiAlternatives
from django.db.models import Q
from django.template.loader import render_to_string
from django.utils import timezone
import logging

from .models import Player
from character.models import PlayerCharacterLink

User = get_user_model()

logger = logging.getLogger("general")

# A connection is considered abandoned (worker crash, OOM kill, deploy
# restart) if `last_seen` hasn't been stamped for this long. Stamped
# server-side by TimerConsumer for as long as it holds the socket, so a
# lapse means the process is gone, not that the player's tab is idle.
STALE_CONNECTION_THRESHOLD = timedelta(minutes=10)


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
        player.is_online = False
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


@shared_task
def reconcile_stale_online_players():
    """
    Clears `is_online`/`active_connections` for players whose websocket
    connection was never cleanly closed (worker crash, OOM kill, deploy
    restart bypasses TimerConsumer.disconnect()), so the online-count
    badge can't drift upward forever. A player is considered stale once
    their `last_seen` heartbeat (refreshed on every websocket ping) is
    older than STALE_CONNECTION_THRESHOLD, or was never set.
    """
    cutoff = timezone.now() - STALE_CONNECTION_THRESHOLD
    stale_players = Player.objects.filter(is_online=True).filter(
        Q(last_seen__isnull=True) | Q(last_seen__lt=cutoff)
    )
    updated = stale_players.update(active_connections=0, is_online=False)

    if updated:
        logger.info(f"[RECONCILE ONLINE PLAYERS] Reset {updated} stale player(s).")
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            "online_users",
            {
                "type": "online_count",
                "count": Player.online_count(),
            },
        )


@shared_task
def invite_waitlist_entries():
    from users.services import waitlist_service

    count = waitlist_service.invite_up_to_headroom()
    logger.info(f"[WAITLIST INVITE TASK] Invited {count} waitlist entrant(s).")
    return count


@shared_task
def send_waitlist_nudges():
    from users.services import waitlist_service

    count = waitlist_service.send_due_nudges()
    logger.info(f"[WAITLIST NUDGE TASK] Sent {count} waitlist nudge/removal email(s).")
    return count


@shared_task
def send_inactivity_reminders():
    from users.services import inactivity_reminder_service

    count = inactivity_reminder_service.send_due_reminders()
    logger.info(
        f"[INACTIVITY REMINDER TASK] Sent {count} inactivity reminder email(s)."
    )
    return count


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
