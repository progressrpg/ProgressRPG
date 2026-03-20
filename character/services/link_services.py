from __future__ import annotations

import logging
from django.utils import timezone

logger = logging.getLogger("general")
logger_errors = logging.getLogger("errors")


def player_link_get_character(model_cls, player):
    links = model_cls.objects.filter(player=player, is_active=True)
    if not links.exists():
        raise ValueError("No active Character found for this player.")

    if links.count() > 1:
        logger.warning(
            f"[PLAYER] Multiple active characters found for player {player.id} — returning the first one"
        )

    return links.first().character


def player_link_get_player(model_cls, character):
    links = model_cls.objects.filter(character=character, is_active=True)
    if not links.exists():
        raise ValueError("Character has no active Player link.")

    if links.count() > 1:
        logger.warning(
            f"[PLAYER] Multiple active player links found for character {character.id} — returning the first one"
        )

    return links.first().player


def player_link_unlink(link) -> None:
    link.unlinked_at = timezone.now()
    link.is_active = False
    link.save()
    link.character.can_link = True
    link.character.save(update_fields=["can_link"])


def player_link_deactivate_active_links(model_cls, player) -> None:
    for link in model_cls.objects.filter(player=player, is_active=True):
        player_link_unlink(link)


def player_link_deactivate_active_links_for_character(model_cls, character) -> None:
    for link in model_cls.objects.filter(character=character, is_active=True):
        player_link_unlink(link)


def player_link_assign_character(model_cls, player, character):
    player_link_deactivate_active_links(model_cls, player)
    player_link_deactivate_active_links_for_character(model_cls, character)
    link = model_cls.objects.create(
        player=player,
        character=character,
        is_active=True,
    )
    character.can_link = False
    character.save(update_fields=["can_link"])
    return link
