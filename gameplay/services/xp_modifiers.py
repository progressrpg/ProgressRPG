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
# Grace window before an activity_active modifier actually ends once a
# player stops timing, so a gap between a character's activity blocks (or a
# quick pause/resume) doesn't drop and reactivate the boost - see issue #750.
ACTIVITY_ACTIVE_GRACE_MINUTES = 5


@transaction.atomic
def activate_link_modifier(
    *,
    link,
    key: str,
    multiplier,
    scope=XpModifier.Scope.CHARACTER,
    duration=None,
    ends_at=None,
    now=None,
):
    now = now or timezone.now()
    if ends_at is None and duration is not None:
        ends_at = now + duration

    owner_field = "character" if scope == XpModifier.Scope.CHARACTER else "player"
    owner = link.character if scope == XpModifier.Scope.CHARACTER else link.player

    mod, _created = XpModifier.objects.update_or_create(
        scope=scope,
        key=key,
        **{owner_field: owner},
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
    """
    Called when a player disconnects: keep the player_online modifier active
    for `cooldown_minutes` instead of ending it immediately, so a brief
    reconnect doesn't cost the character its boost, then let the scheduled
    Celery task end it if the player doesn't come back in time.
    """
    now = timezone.now()
    ends_at = now + timedelta(minutes=cooldown_minutes)

    mod = activate_link_modifier(
        link=link,
        key=PLAYER_ONLINE_KEY,
        multiplier=PLAYER_ONLINE_MULTIPLIER,
        now=now,
    )
    return schedule_modifier_end(mod=mod, ends_at=ends_at)


@transaction.atomic
def handle_online_login(player: Player):
    """
    Called whenever a player is confirmed online (login, or any
    authenticated poll while connected): (re)activate the player_online
    character modifier and cancel any cooldown-end task left over from a
    previous disconnect.
    """
    link = player.active_link
    if not link:
        return None
    link = PlayerCharacterLink.objects.select_related("character").get(id=link.id)

    mod = activate_link_modifier(
        link=link,
        key=PLAYER_ONLINE_KEY,
        multiplier=PLAYER_ONLINE_MULTIPLIER,
    )
    if mod.task_id:
        current_app.control.revoke(mod.task_id)
        mod.task_id = None
        mod.save(update_fields=["task_id"])
    return mod


@transaction.atomic
def set_activity_active_modifiers(player: Player, *, is_active: bool):
    """
    Toggle activity-active modifiers without replacing still-valid online modifiers.

    - Character gets a higher bonus while player is actively recording.
    - Player gets their own bonus while actively recording.

    Stopping doesn't end the modifiers outright: `ends_at` is pushed out by
    ACTIVITY_ACTIVE_GRACE_MINUTES and a Celery task is scheduled to end them
    then. If the player starts another activity within that window,
    activate_link_modifier's update_or_create refreshes the same modifier
    row (and the pending end task is cancelled) rather than dropping and
    reactivating it.
    """
    link = player.active_link
    if not link:
        return []

    link = PlayerCharacterLink.objects.select_related("character", "player").get(
        id=link.id
    )

    if is_active:
        mods = [
            activate_link_modifier(
                link=link,
                key=ACTIVITY_ACTIVE_KEY,
                multiplier=ACTIVITY_ACTIVE_CHARACTER_MULTIPLIER,
                scope=XpModifier.Scope.CHARACTER,
            ),
            activate_link_modifier(
                link=link,
                key=ACTIVITY_ACTIVE_KEY,
                multiplier=ACTIVITY_ACTIVE_PLAYER_MULTIPLIER,
                scope=XpModifier.Scope.PLAYER,
            ),
        ]
        for mod in mods:
            if mod.task_id:
                current_app.control.revoke(mod.task_id)
                mod.task_id = None
                mod.save(update_fields=["task_id"])
        return mods

    grace_ends_at = timezone.now() + timedelta(minutes=ACTIVITY_ACTIVE_GRACE_MINUTES)
    mods = []
    for scope, owner_field, owner in (
        (XpModifier.Scope.CHARACTER, "character", link.character),
        (XpModifier.Scope.PLAYER, "player", link.player),
    ):
        mod = (
            XpModifier.objects.filter(
                scope=scope, key=ACTIVITY_ACTIVE_KEY, **{owner_field: owner}
            )
            .order_by("-starts_at")
            .first()
        )
        if mod and mod.is_active:
            mods.append(schedule_modifier_end(mod=mod, ends_at=grace_ends_at))

    return mods
