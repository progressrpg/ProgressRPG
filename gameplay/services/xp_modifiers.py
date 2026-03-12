from celery import current_app
from datetime import timedelta
from django.utils import timezone
from django.db import transaction

from character.models import PlayerCharacterLink
from gameplay.models import XpModifier
from gameplay.tasks import end_online_boost
from users.models import Player

PLAYER_ONLINE_KEY = "player_online"
PLAYER_ONLINE_MULTIPLIER = 1.25
ACTIVITY_ACTIVE_KEY = "activity_active"
ACTIVITY_ACTIVE_CHARACTER_MULTIPLIER = 1.5
ACTIVITY_ACTIVE_PLAYER_MULTIPLIER = 1.25


@transaction.atomic
def activate_link_modifier(
    *, link, key: str, multiplier, duration=None, ends_at=None, now=None
):
    now = now or timezone.now()
    if ends_at is None and duration is not None:
        ends_at = now + duration

    mod, _created = XpModifier.objects.update_or_create(
        scope=XpModifier.Scope.CHARACTER,
        character=link.character,
        key=key,
        defaults={
            "multiplier": multiplier,
            "starts_at": now,
            "ends_at": ends_at,
            "is_active": True,
        },
    )
    return mod


@transaction.atomic
def end_modifier(mod: XpModifier, *, now=None):
    now = now or timezone.now()
    mod.ends_at = now
    mod.is_active = False
    mod.task_id = None
    mod.save(update_fields=["ends_at", "is_active", "task_id"])
    return mod


@transaction.atomic
def schedule_modifier_end(
    *,
    mod: XpModifier,
    ends_at,
    task=end_online_boost,
    task_kwargs=None,
):
    """
    Set ends_at and schedule a Celery task. Stores task_id on the modifier.
    """
    # Revoke any previous scheduled end
    if mod.task_id:
        current_app.control.revoke(mod.task_id)

    mod.ends_at = ends_at
    mod.is_active = True
    mod.save(update_fields=["ends_at", "is_active"])

    if task_kwargs is None:
        task_kwargs = {"modifier_id": mod.id}

    result = task.apply_async(kwargs=task_kwargs, eta=ends_at)

    mod.task_id = result.id
    mod.save(update_fields=["task_id"])
    return mod


@transaction.atomic
def schedule_online_end(link: PlayerCharacterLink, cooldown_minutes=30):
    now = timezone.now()
    ends_at = now + timedelta(minutes=cooldown_minutes)

    # Upsert your modifier row:
    mod = (
        XpModifier.objects.filter(
            scope=XpModifier.Scope.CHARACTER,
            character=link.character,
            key=PLAYER_ONLINE_KEY,
        )
        .order_by("-starts_at")
        .first()
    )
    if mod:
        # keep the original starts_at; just update multiplier/ends_at
        mod.multiplier = PLAYER_ONLINE_MULTIPLIER
        mod.is_active = True
        mod.save(update_fields=["multiplier", "is_active"])
    else:
        mod = XpModifier.objects.create(
            scope=XpModifier.Scope.CHARACTER,
            character=link.character,
            key=PLAYER_ONLINE_KEY,
            multiplier=PLAYER_ONLINE_MULTIPLIER,
            starts_at=now,
            ends_at=None,
            is_active=True,
        )

    return schedule_modifier_end(mod=mod, ends_at=ends_at)


@transaction.atomic
def handle_online_login(player: Player):
    link = player.active_link
    if not link:
        return None
    link = PlayerCharacterLink.objects.get(id=link.id)
    mod = (
        XpModifier.objects.filter(
            scope=XpModifier.Scope.CHARACTER,
            character=link.character,
            key=PLAYER_ONLINE_KEY,
        )
        .order_by("-starts_at")
        .first()
    )

    now = timezone.now()

    if not mod:
        mod = XpModifier.objects.create(
            scope=XpModifier.Scope.CHARACTER,
            character=link.character,
            key=PLAYER_ONLINE_KEY,
            multiplier=PLAYER_ONLINE_MULTIPLIER,
            starts_at=now,
            ends_at=None,
            is_active=True,
            task_id=None,
        )
        return mod
    # Revoke scheduled end if present
    if mod.task_id:
        current_app.control.revoke(mod.task_id)
        mod.task_id = None

    mod.multiplier = PLAYER_ONLINE_MULTIPLIER
    mod.is_active = True
    mod.ends_at = None
    mod.save(update_fields=["multiplier", "is_active", "ends_at", "task_id"])
    return mod


@transaction.atomic
def set_activity_active_modifiers(player: Player, *, is_active: bool):
    """
    Toggle activity-active modifiers without replacing still-valid online modifiers.

    - Character gets a higher bonus while player is actively recording.
    - Player gets their own bonus while actively recording.
    """
    link = player.active_link
    if not link:
        return []

    link = PlayerCharacterLink.objects.select_related("character", "player").get(
        id=link.id
    )
    now = timezone.now()

    character_mod = (
        XpModifier.objects.filter(
            scope=XpModifier.Scope.CHARACTER,
            character=link.character,
            key=ACTIVITY_ACTIVE_KEY,
        )
        .order_by("-starts_at")
        .first()
    )
    if not character_mod and is_active:
        character_mod = XpModifier.objects.create(
            scope=XpModifier.Scope.CHARACTER,
            character=link.character,
            key=ACTIVITY_ACTIVE_KEY,
            multiplier=ACTIVITY_ACTIVE_CHARACTER_MULTIPLIER,
            starts_at=now,
            ends_at=None,
            is_active=True,
            task_id=None,
        )
    elif character_mod:
        character_mod.multiplier = ACTIVITY_ACTIVE_CHARACTER_MULTIPLIER
        character_mod.is_active = is_active
        character_mod.ends_at = None if is_active else now
        character_mod.task_id = None
        character_mod.save(
            update_fields=["multiplier", "is_active", "ends_at", "task_id"]
        )

    player_mod = (
        XpModifier.objects.filter(
            scope=XpModifier.Scope.PLAYER,
            player=link.player,
            key=ACTIVITY_ACTIVE_KEY,
        )
        .order_by("-starts_at")
        .first()
    )
    if not player_mod and is_active:
        player_mod = XpModifier.objects.create(
            scope=XpModifier.Scope.PLAYER,
            player=link.player,
            key=ACTIVITY_ACTIVE_KEY,
            multiplier=ACTIVITY_ACTIVE_PLAYER_MULTIPLIER,
            starts_at=now,
            ends_at=None,
            is_active=True,
            task_id=None,
        )
    elif player_mod:
        player_mod.multiplier = ACTIVITY_ACTIVE_PLAYER_MULTIPLIER
        player_mod.is_active = is_active
        player_mod.ends_at = None if is_active else now
        player_mod.task_id = None
        player_mod.save(update_fields=["multiplier", "is_active", "ends_at", "task_id"])

    return [m for m in [character_mod, player_mod] if m]
