from gameplay.models import ActivityTimer
from users.models import Player
from users.validators import generate_default_player_name


def verified_user_count():
    """Count users who have completed email confirmation.

    Used for the registration cap so unconfirmed signups (bots, abandoned
    signups) can't exhaust it and block real users.
    """
    from django.contrib.auth import get_user_model

    return get_user_model().objects.filter(is_confirmed=True).count()


def ensure_player_setup_for_user(user, raw=False):
    """Ensure player setup exists for a user unless raw mode is requested."""
    if raw:
        return None

    player, _ = Player.objects.get_or_create(user=user)

    if not player.name:
        player.name = generate_default_player_name(player.id)
        player.save(update_fields=["name"])

    ActivityTimer.objects.get_or_create(player=player)
    return player
