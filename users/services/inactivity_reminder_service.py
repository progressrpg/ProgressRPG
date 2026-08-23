from datetime import date
from typing import Any, Optional

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from progression.day_boundaries import logical_date_for
from users.utils import send_email_to_users

User = get_user_model()

INACTIVITY_THRESHOLD_DAYS = 7


def get_last_active_logical_date(user) -> Optional[date]:
    """
    The last logical day (per progression.day_boundaries - respecting this
    user's own day_start_time/timezone, not a raw calendar date) on which
    they logged in or recorded an activity session, or None if they never
    have. Combines three sources since no single one is authoritative:
    `last_login` (stamped by Django auth on every login),
    `UserLogin.last_recorded_login` (this app's own login log), and the
    most recent `PlayerActivity` (a completed or in-progress timer/task
    session).
    """
    from progression.models import PlayerActivity
    from users.models import UserLogin

    instants = [user.last_login, UserLogin.last_recorded_login(user)]

    player = getattr(user, "player", None)
    if player is not None:
        latest_activity_at = (
            PlayerActivity.objects.filter(player=player)
            .order_by("-created_at")
            .values_list("created_at", flat=True)
            .first()
        )
        instants.append(latest_activity_at)

    logical_dates = [logical_date_for(user, i) for i in instants if i is not None]
    return max(logical_dates) if logical_dates else None


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
    Scans opted-in users for exactly 7 logical days of inactivity (no
    recorded login or activity session) and sends each a reminder email.
    "Logical day" means per-user, honouring their own
    day_start_time/timezone (progression.day_boundaries) rather than a raw
    168-hour window, so the boundary lands consistently regardless of what
    time of day their last activity happened to fall at.

    Deliberately exact-equality, not >=: a user's gap only reads exactly 7
    on the single logical day it first reaches the threshold, then reads 8,
    9, ... on every day after - so with the daily beat schedule running
    once a day, the check is self-idempotent and needs no separate
    "already sent" record. That also means a fresh 7-day gap after renewed
    activity naturally triggers another reminder with no extra bookkeeping.
    The tradeoff: if a scheduled scan is ever skipped (worker downtime) or
    run twice in the same day, there's no record to catch up a missed send
    or suppress a duplicate one - accepted here in exchange for not needing
    a model/field per reminder category.

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

    candidates = User.objects.filter(is_active=True, pending_delete=False)

    sent_count = 0
    for user in candidates.iterator():
        if not user.preferences["notifications__inactivity_reminder_emails"]:
            continue

        last_active_date = get_last_active_logical_date(user)
        if last_active_date is None:
            continue

        today = logical_date_for(user, now)
        if (today - last_active_date).days != INACTIVITY_THRESHOLD_DAYS:
            continue
        if last_active_date < logical_date_for(user, cutoff):
            continue

        send_reminder_email(user)
        sent_count += 1

    return sent_count
