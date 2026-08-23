from datetime import datetime, timedelta
from typing import Any, Optional

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from users.utils import send_email_to_users

User = get_user_model()

INACTIVITY_THRESHOLD_DAYS = 7


def get_last_active_at(user) -> Optional[datetime]:
    """
    The instant of this user's most recent recorded login or activity
    session, or None if they have neither. Combines three sources since no
    single one is authoritative: `last_login` (stamped by Django auth on
    every login), `UserLogin.last_recorded_login` (this app's own login
    log), and the most recent `PlayerActivity` (a completed or in-progress
    timer/task session).
    """
    from progression.models import PlayerActivity
    from users.models import UserLogin

    candidates = [user.last_login, UserLogin.last_recorded_login(user)]

    player = getattr(user, "player", None)
    if player is not None:
        latest_activity_at = (
            PlayerActivity.objects.filter(player=player)
            .order_by("-created_at")
            .values_list("created_at", flat=True)
            .first()
        )
        candidates.append(latest_activity_at)

    active_at = [c for c in candidates if c is not None]
    return max(active_at) if active_at else None


def send_reminder_email(user) -> None:
    from django.conf import settings

    context: dict[str, Any] = {
        "current_year": timezone.now().year,
        "frontend_url": getattr(settings, "FRONTEND_URL", "http://localhost:5173"),
    }
    transaction.on_commit(
        lambda: send_email_to_users(
            users=[user],
            subject="We miss you at Progress RPG",
            template_base="emails/inactivity_reminder",
            context=context,
            cc_admin=False,
        )
    )


def send_due_reminders() -> int:
    """
    Scans opted-in users for 7+ days of inactivity (no recorded login or
    activity session) and sends each a one-time reminder email. Sends once
    per inactivity period: a user isn't reminded again until they've been
    active since their last reminder, at which point a fresh 7-day
    inactivity period can trigger another one.

    No-op while `GameSettings.inactivity_reminders_enabled_from` is unset
    (rollout is opt-in, mirroring the waitlist nudge cutoff). Users already
    past the threshold with no activity since before that cutoff are
    excluded too, so turning the feature on doesn't burst-send to
    long-dormant accounts.
    """
    from core.models import GameSettings

    cutoff = GameSettings.current().inactivity_reminders_enabled_from
    if cutoff is None:
        return 0

    now = timezone.now()
    threshold = now - timedelta(days=INACTIVITY_THRESHOLD_DAYS)

    candidates = User.objects.filter(
        is_active=True,
        pending_delete=False,
        receives_inactivity_reminder=True,
    )

    sent_count = 0
    for user in candidates.iterator():
        last_active_at = get_last_active_at(user)
        if last_active_at is None or last_active_at > threshold:
            continue
        if last_active_at < cutoff:
            continue
        if (
            user.inactivity_reminder_sent_at is not None
            and user.inactivity_reminder_sent_at >= last_active_at
        ):
            continue  # already reminded for this inactivity period

        updated = (
            User.objects.filter(pk=user.pk, receives_inactivity_reminder=True)
            .filter(
                Q(inactivity_reminder_sent_at__isnull=True)
                | Q(inactivity_reminder_sent_at__lt=last_active_at)
            )
            .update(inactivity_reminder_sent_at=now)
        )

        if updated:
            send_reminder_email(user)
            sent_count += 1

    return sent_count
