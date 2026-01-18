# character.signals
from datetime import timedelta, datetime, time
from django.contrib.auth.signals import user_logged_in
from django.db import transaction
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.utils import timezone

from .models import Character, PlayerCharacterLink, Behaviour

from gameplay.models import QuestTimer
from progression.models import CharacterActivity

@receiver(post_save, sender=Character)
def create_timer(sender, instance, created, **kwargs):
    """Create a quest timer for a new character"""
    if created:
        quest_timer = QuestTimer.objects.create(character=instance)


@receiver(post_save, sender=Character)
def create_behaviour(sender, instance, created, **kwargs):
    """Create a behaviour instance for a new character"""
    if created:
        behaviour = Behaviour.objects.create(character=instance)


@receiver(pre_delete, sender=PlayerCharacterLink)
def unlink_before_deletion(sender, instance, **kwargs):
    character = instance.character
    character.is_npc = True
    character.save(update_fields=["is_npc"])

    instance.unlink()

@receiver(user_logged_in)
@transaction.atomic
def update_character_behaviour_on_login(sender, request, user, **kwargs):
    if request.path.startswith("/admin/"):
        return  # skip admin logins

    today = timezone.now().date()
    character = user.profile.current_character
    character.behaviour.sync_to_now()

    yesterday = today - timedelta(days=1)

    ensure_day_activities(character, today)
    ensure_day_activities(character, yesterday)

def window_for_date(date, behaviour):
    # reuse Behaviour logic (returns dawn, dusk, next_dawn); use it to get the sleep tail
    dawn, dusk, next_dawn = behaviour._day_window(date)
    tz = timezone.get_current_timezone()
    window_start = timezone.make_aware(datetime.combine(date, time(0, 0)), tz)
    # include sleep tail so checks match generate_day's delete logic
    # sleep_end is the tail returned via next_dawn for the following day; generate_day uses its computed sleep_end
    # fallback to end-of-day if you don't want the tail
    window_end = next_dawn  # or timezone.make_aware(datetime.combine(date, time(23,59,59)), tz)
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