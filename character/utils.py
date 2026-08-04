from datetime import timedelta, datetime, time
from django.utils import timezone
import logging
from progression.models import CharacterActivity

logger = logging.getLogger("general")


def window_for_date(date, behaviour):
    # reuse Behaviour logic (returns dawn, dusk, next_dawn); use it to get the sleep tail
    dawn, dusk, next_dawn = behaviour._day_window(date)
    tz = timezone.get_current_timezone()
    window_start = timezone.make_aware(datetime.combine(date, time(0, 0)), tz)
    # include sleep tail so checks match generate_day's delete logic
    # sleep_end is the tail returned via next_dawn for the following day; generate_day uses its computed sleep_end
    # fallback to end-of-day if you don't want the tail
    window_end = (
        next_dawn  # or timezone.make_aware(datetime.combine(date, time(23,59,59)), tz)
    )
    return window_start, window_end


def activities_exist_for_date(character, date):
    window_start, window_end = window_for_date(date, character.behaviour)
    return CharacterActivity.objects.filter(
        character=character,
        scheduled_start__lt=window_end,
        scheduled_end__gt=window_start,
    ).exists()


def ensure_day_activities(character, date, create_if_missing=True):
    if not activities_exist_for_date(character, date) and create_if_missing:
        # generate_day is atomic and does cleanup/select_for_update internally
        return character.behaviour.generate_day(date)
    return None


def work_activities_for(character):
    """
    "work" ActivityDefinitions available to a character for their
    CharacterActivity work blocks - filtered by the roles the character
    holds and their current proficiency (see SkillDefinition.is_unlocked_for).
    Skill-less definitions have no role requirement and are always included,
    forming a general-work fallback pool for characters without a role yet.
    """
    from progression.models import ActivityDefinition, Role

    held_role_ids = set(
        Role.objects.filter(character_roles__character=character).values_list(
            "id", flat=True
        )
    )

    return [
        activity
        for activity in ActivityDefinition.objects.filter(
            kind=ActivityDefinition.Kind.WORK
        ).select_related("skill", "skill__role")
        if activity.skill_id is None
        or (
            (activity.skill.role_id is None or activity.skill.role_id in held_role_ids)
            and activity.skill.is_unlocked_for(character)
        )
    ]
