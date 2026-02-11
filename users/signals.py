# user.signals
from allauth.account.signals import email_confirmed
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.contrib.auth.signals import user_logged_in
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
import logging

from .models import Player
from .utils import assign_character_to_player

from gameplay.models import ServerMessage

logger = logging.getLogger("general")

User = get_user_model()


@receiver(email_confirmed)
def set_user_confirmed(sender, request, email_address, **kwargs):
    user = email_address.user
    User.objects.filter(pk=user.pk).update(is_confirmed=True)


@receiver(post_save, sender=User)
def create_player(sender, instance, created, raw=False, **kwargs):
    """Create a player for the user when a new user is created"""
    if raw:
        return
    if created:
        email_prefix = (instance.email or "").split("@", 1)[0].strip()
        Player.objects.get_or_create(
            user=instance,
            defaults={"name": email_prefix or None},
        )


@receiver(post_save, sender=Player)
def assign_character(sender, instance, created, raw=False, **kwargs):
    """Assign character when player created"""
    if raw:
        return
    if created:
        assign_character_to_player(instance)


@receiver(user_logged_in)
def update_login_streak(sender, request, user: User, **kwargs):
    if request.path.startswith("/admin/"):
        return  # skip admin logins
    if user.last_login and timezone.now() - user.last_login < timedelta(hours=24):
        return
    player = Player.objects.filter(user=user).first()
    today = timezone.now().date()

    logger.info(
        f"[UPDATE LOGIN STREAK] Updating login streak for {user.email}. Last login: {player.last_login}"
    )
    message_text = ""
    if player.last_login.date() == today:
        message_text = f"Welcome back! You logged in earlier today."
    elif player.last_login.date() == today - timedelta(days=1):
        player.login_streak += 1  # Continue the streak
        message_text = f"Welcome back! You logged in yesterday. Your login streak is now {player.login_streak} days."
    else:
        player.login_streak = 1  # Reset streak
        message_text = f"Welcome back, we missed you! Your login streak has been reset."

    if player.login_streak_max < player.login_streak:
        player.login_streak_max = player.login_streak

    ServerMessage.objects.create(
        group=player.group_name,
        type="notification",
        action="notification",
        data={},
        message=message_text,
        is_draft=False,
    )

    player.last_login = timezone.now()
    player.total_logins += 1
    player.save()
