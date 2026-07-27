import secrets
from datetime import timedelta
from typing import Any, NotRequired, TypedDict

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from users.models import Waitlist
from users.services.registration_services import verified_user_count
from users.utils import send_email_to_users


class _NudgeMilestone(TypedDict):
    days: int
    field: str
    template: str
    terminal: NotRequired[bool]


NUDGE_SCHEDULE: list[_NudgeMilestone] = [
    {"days": 3, "field": "nudge_3day_sent_at", "template": "waitlist_nudge_message"},
    {"days": 7, "field": "nudge_7day_sent_at", "template": "waitlist_nudge_message"},
    {"days": 30, "field": "nudge_30day_sent_at", "template": "waitlist_nudge_message"},
    {
        "days": 60,
        "field": "nudge_removal_sent_at",
        "template": "waitlist_removed_message",
        "terminal": True,
    },
]


def generate_invite_token() -> str:
    return secrets.token_urlsafe(32)


def build_invite_url(token: str) -> str:
    frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:5173")
    return f"{frontend_url}/waitlist/redeem/{token}"


def send_signup_confirmation_email(entry: Waitlist) -> None:
    """Sends the "you're on the waitlist" confirmation for a new signup."""
    context: dict[str, Any] = {"current_year": timezone.now().year}
    transaction.on_commit(
        lambda: send_email_to_users(
            users=[entry.email],
            subject="You're on the Progress RPG waitlist",
            template_base="emails/waitlist_signup_confirmation",
            context=context,
            cc_admin=False,
        )
    )


def send_invite_email(entry: Waitlist) -> None:
    """Queues (or re-queues) the invitation email for an already-invited entry."""
    assert entry.invite_token, "send_invite_email requires an already-invited entry"
    context: dict[str, Any] = {
        "invite_url": build_invite_url(entry.invite_token),
        "current_year": timezone.now().year,
    }
    transaction.on_commit(
        lambda: send_email_to_users(
            users=[entry.email],
            subject="You're invited to Progress RPG",
            template_base="emails/waitlist_invite_message",
            context=context,
            cc_admin=False,
        )
    )


def invite_entry(entry: Waitlist) -> Waitlist:
    """Promotes a waiting entry to invited and sends the invite email. Idempotent token: only generates one if absent."""
    if not entry.invite_token:
        entry.invite_token = generate_invite_token()
    entry.status = Waitlist.Status.INVITED
    entry.invited_at = timezone.now()
    entry.save(update_fields=["invite_token", "status", "invited_at"])
    send_invite_email(entry)
    return entry


def resend_invite_email(entry: Waitlist) -> Waitlist:
    """Resends the existing invitation without touching token, invited_at, or queue position."""
    send_invite_email(entry)
    return entry


def invite_up_to_headroom() -> int:
    """Invites waiting entries (oldest first) up to whatever headroom exists under the registration cap."""
    from core.models import GameSettings

    with transaction.atomic():
        registration_cap = GameSettings.current().registration_cap
        registered = verified_user_count()
        headroom = registration_cap - registered
        if headroom <= 0:
            return 0

        candidate_ids = list(
            Waitlist.objects.filter(status=Waitlist.Status.WAITING)
            .order_by("signup_timestamp")
            .values_list("id", flat=True)[:headroom]
        )
        if not candidate_ids:
            return 0

        entries = list(
            Waitlist.objects.select_for_update(skip_locked=True)
            .filter(id__in=candidate_ids, status=Waitlist.Status.WAITING)
            .order_by("signup_timestamp")
        )
        for entry in entries:
            invite_entry(entry)
        return len(entries)


def send_nudge_email(entry: Waitlist, template: str, days: int) -> None:
    is_removal = template == "waitlist_removed_message"
    context: dict[str, Any] = {
        "day": days,
        "current_year": timezone.now().year,
    }
    if is_removal:
        context["frontend_url"] = getattr(
            settings, "FRONTEND_URL", "http://localhost:5173"
        )
    else:
        assert entry.invite_token, "send_nudge_email requires an already-invited entry"
        context["invite_url"] = build_invite_url(entry.invite_token)

    subject = (
        "You've been removed from the Progress RPG waitlist"
        if is_removal
        else "Still there? Your Progress RPG invite is waiting"
    )
    transaction.on_commit(
        lambda: send_email_to_users(
            users=[entry.email],
            subject=subject,
            template_base=f"emails/{template}",
            context=context,
            cc_admin=False,
        )
    )


def send_due_nudges() -> int:
    """
    Scans INVITED waitlist entries for each configured milestone in
    NUDGE_SCHEDULE and sends the corresponding nudge/removal email to
    entries that have crossed that milestone's age and haven't already
    received it. The terminal (60-day) milestone also flips status to
    REMOVED. Entries invited before GameSettings.waitlist_nudges_enabled_from
    are excluded so a rollout deploy can't burst-send/remove existing
    long-invited entries.
    """
    from core.models import GameSettings

    now = timezone.now()
    cutoff = GameSettings.current().waitlist_nudges_enabled_from
    if cutoff is None:
        return 0

    sent_count = 0
    for milestone in NUDGE_SCHEDULE:
        field = milestone["field"]
        due_at = now - timedelta(days=milestone["days"])
        entries = Waitlist.objects.filter(
            status=Waitlist.Status.INVITED,
            invited_at__gte=cutoff,
            invited_at__lte=due_at,
            **{f"{field}__isnull": True},
        )
        for entry in entries:
            send_nudge_email(entry, milestone["template"], milestone["days"])

            update_fields: dict[str, Any] = {field: now}
            if milestone.get("terminal"):
                update_fields["status"] = Waitlist.Status.REMOVED

            updated = Waitlist.objects.filter(
                pk=entry.pk,
                status=Waitlist.Status.INVITED,
                **{f"{field}__isnull": True},
            ).update(**update_fields)
            sent_count += updated

    return sent_count
