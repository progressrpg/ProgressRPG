# progression/services.py
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from .models import OfflineActivityLedger, PlayerActivity, Task
from .day_boundaries import logical_date_for

# Offline-logged activities are recorded for completeness/history at any
# tier, but only earn XP for premium accounts, subject to the daily caps
# below (issue #630).
OFFLINE_DAILY_DURATION_CAP_SECONDS = 16 * 3600
OFFLINE_DAILY_XP_ELIGIBLE_CAP_SECONDS = 6 * 3600
OFFLINE_XP_ELIGIBLE_BACKDATE_WINDOW = timedelta(days=7)


@dataclass
class OfflineActivityLogResult:
    activity: PlayerActivity
    reward_summary: Dict[str, Any]
    xp_eligible_seconds: int
    level_ups: list


@transaction.atomic
def log_offline_activity(
    player,
    *,
    name: str,
    description: str = "",
    skill=None,
    task: Optional[Task] = None,
    started_at: datetime,
    completed_at: datetime,
) -> OfflineActivityLogResult:
    """
    Record a completed activity after the fact, without a live timer session.

    Creates a completed, backdated ``PlayerActivity`` (origin="manual")
    attached to ``task`` (created automatically if not supplied). XP is
    awarded using the same reward calculation as timer-based completion,
    but only for premium accounts, only for time within the last
    ``OFFLINE_XP_ELIGIBLE_BACKDATE_WINDOW``, and capped at
    ``OFFLINE_DAILY_XP_ELIGIBLE_CAP_SECONDS`` of XP-eligible seconds per
    calendar day. Total logged time (XP-eligible or not) is separately
    capped at ``OFFLINE_DAILY_DURATION_CAP_SECONDS`` per calendar day as a
    plausibility ceiling. Runs atomically so a failed cap check never
    leaves behind an orphaned, auto-created task.
    """
    if completed_at <= started_at:
        raise ValidationError("completed_at must be after started_at.")

    now = timezone.now()
    if completed_at > now:
        raise ValidationError("Cannot log an activity that completes in the future.")

    duration = int((completed_at - started_at).total_seconds())
    # The player's logical day, not the server's calendar day - the daily
    # caps below and the activity's own attribution have to agree.
    log_date = logical_date_for(player, started_at)

    ledger, _created = OfflineActivityLedger.objects.select_for_update().get_or_create(
        player=player, date=log_date
    )

    if ledger.logged_seconds + duration > OFFLINE_DAILY_DURATION_CAP_SECONDS:
        cap_hours = OFFLINE_DAILY_DURATION_CAP_SECONDS // 3600
        raise ValidationError(
            f"Logging this activity would exceed the {cap_hours}-hour daily "
            f"limit on offline-logged time for {log_date.isoformat()}."
        )

    within_xp_window = now - completed_at <= OFFLINE_XP_ELIGIBLE_BACKDATE_WINDOW
    xp_eligible_seconds = 0
    if player.is_premium and within_xp_window:
        remaining_xp_budget = max(
            0, OFFLINE_DAILY_XP_ELIGIBLE_CAP_SECONDS - ledger.xp_eligible_seconds
        )
        xp_eligible_seconds = min(duration, remaining_xp_budget)

    if task is None:
        task = Task.objects.create(player=player, name=name)

    activity = PlayerActivity.objects.create(
        player=player,
        name=name,
        description=description,
        skill=skill,
        task=task,
        origin=PlayerActivity.Origin.MANUAL,
        started_at=started_at,
        logical_date=log_date,
        duration=duration,
    )

    reward_summary = activity.get_xp_reward_summary(duration=xp_eligible_seconds)
    xp_gained = activity.complete(
        reward_summary=reward_summary, completed_at=completed_at
    )

    ledger.logged_seconds += duration
    ledger.xp_eligible_seconds += xp_eligible_seconds
    ledger.save(update_fields=["logged_seconds", "xp_eligible_seconds", "last_updated"])

    level_ups = player.add_activity(duration, xp=xp_gained) if xp_gained else []

    from .daily_goals import check_and_award_daily_goals

    # Awarded against the day the activity happened on, not today - a
    # session logged after the fact belongs to the day it was worked.
    _goals_state, bonus_level_ups = check_and_award_daily_goals(player, today=log_date)
    level_ups = level_ups + bonus_level_ups

    return OfflineActivityLogResult(
        activity=activity,
        reward_summary=reward_summary,
        xp_eligible_seconds=xp_eligible_seconds,
        level_ups=level_ups,
    )
