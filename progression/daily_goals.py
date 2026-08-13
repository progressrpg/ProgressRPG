# progression/daily_goals.py
"""
Daily goals for the map-view badge (issue #751, replacing the old
`points_today` mechanic from issue #673).

Three intentionally easy, binary-ish goals for the player's *current* day:

1. Logged in today.
2. Completed at least one activity today.
3. Recorded at least ``MINUTES_GOAL_THRESHOLD`` minutes of activity time
   today (cumulative across activities, not a per-activity minimum).

Clearing all three once in a day awards a one-off lump-sum AP bonus via the
existing AP system (``Player.add_activity``) - see ``DailyGoalAward`` for
the idempotency record that keeps a day's bonus from being paid twice.

"Today" is the current local calendar day (``timezone.localdate()``), the
same convention already used for login streaks (see
``users.models.UserLogin.local_date``) - there's no per-player timezone
stored, so this is the server's configured local timezone, not literally
the player's own.
"""

from dataclasses import dataclass

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from .models import DailyGoalAward

MINUTES_GOAL_THRESHOLD = 3


@dataclass
class DailyGoalsState:
    logged_in_today: bool
    completed_activity_today: bool
    activity_minutes_today: int
    minutes_goal_met: bool
    all_goals_met: bool
    bonus_awarded_today: bool
    bonus_ap: int


def get_daily_goals_state(player, *, today=None) -> DailyGoalsState:
    """
    Compute today's goal state for `player`, live from current data - no
    stored counters to keep in sync, so this is safe to call as often as
    the badge is polled.
    """
    from users.models import UserLogin

    today = today or timezone.localdate()

    logged_in_today = UserLogin.objects.filter(
        user=player.user_id, timestamp__date=today
    ).exists()

    activities_today = player.activities.filter(
        is_complete=True, completed_at__date=today
    )
    completed_activity_today = activities_today.exists()

    total_seconds = activities_today.aggregate(total=Sum("duration"))["total"] or 0
    activity_minutes_today = total_seconds // 60
    minutes_goal_met = activity_minutes_today >= MINUTES_GOAL_THRESHOLD

    all_goals_met = logged_in_today and completed_activity_today and minutes_goal_met

    award = DailyGoalAward.objects.filter(player=player, date=today).first()

    return DailyGoalsState(
        logged_in_today=logged_in_today,
        completed_activity_today=completed_activity_today,
        activity_minutes_today=activity_minutes_today,
        minutes_goal_met=minutes_goal_met,
        all_goals_met=all_goals_met,
        bonus_awarded_today=award is not None,
        bonus_ap=award.bonus_ap if award else 0,
    )


@transaction.atomic
def check_and_award_daily_goals(player, *, today=None):
    """
    Call after a player completes an activity (timer-based or offline-logged
    - anything that can newly satisfy goals 2/3). Idempotently awards the
    completion bonus the first time all three goals are met for `today`.

    Returns (state, level_ups) - state.bonus_ap is the amount just awarded
    (0 if the goals aren't all met yet, or the bonus was already claimed
    earlier today).
    """
    from core.models import GameSettings

    today = today or timezone.localdate()
    state = get_daily_goals_state(player, today=today)

    if not state.all_goals_met or state.bonus_awarded_today:
        return state, []

    # The unique (player, date) constraint on DailyGoalAward is what makes
    # this race-safe: get_or_create falls back to a get() on the
    # IntegrityError from a concurrent completion, so only one caller ever
    # sees created=True for a given day.
    award, created = DailyGoalAward.objects.get_or_create(
        player=player, date=today, defaults={"bonus_ap": 0}
    )
    if not created:
        state.bonus_awarded_today = True
        state.bonus_ap = award.bonus_ap
        return state, []

    bonus_ap = int(GameSettings.current().daily_goals_completion_bonus_ap)
    level_ups = player.add_activity(xp=bonus_ap) if bonus_ap else []

    award.bonus_ap = bonus_ap
    award.save(update_fields=["bonus_ap"])

    state.bonus_awarded_today = True
    state.bonus_ap = bonus_ap
    return state, level_ups
