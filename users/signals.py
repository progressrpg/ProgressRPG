# user.signals
from allauth.account.signals import email_confirmed
from asgiref.sync import async_to_sync
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.contrib.auth.signals import user_logged_in
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
import logging

from .models import Profile
from .utils import assign_character_to_profile

from character.models import PlayerCharacterLink
from gameplay.models import ActivityTimer
from gameplay.models import ServerMessage

logger = logging.getLogger("django")

User = get_user_model()


@receiver(email_confirmed)
def set_user_confirmed(sender, request, email_address, **kwargs):
    user = email_address.user
    user.is_confirmed = True
    user.save()


@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    """Create a profile for the user when a new user is created"""
    if created:
        profile = Profile.objects.create(user=instance)
        logger.info(f"[CREATE PROFILE] New profile {profile.id} created for {instance}")
        ActivityTimer.objects.create(profile=profile)
        logger.info(
            f"[CREATE PROFILE] New activity timer created for profile {profile.id}"
        )


@receiver(post_save, sender=User)
def save_profile(sender, instance, **kwargs):
    """Save the profile when the user is saved"""
    instance.profile.save()


@receiver(post_save, sender=Profile)
def assign_character(sender, instance, created, **kwargs):
    """Assign character when profile created"""
    if created:
        assign_character_to_profile(instance)


@receiver(user_logged_in)
def update_login_streak(sender, request, user, **kwargs):
    if request.path.startswith("/admin/"):
        return  # skip admin logins
    if user.last_login and timezone.now() - user.last_login < timedelta(hours=24):
        return
    profile = user.profile
    today = timezone.now().date()

    logger.info(
        f"[UPDATE LOGIN STREAK] Updating login streak for {user.username}. Last login: {profile.last_login}"
    )
    message_text = ""
    if profile.last_login.date() == today:
        message_text = f"Welcome back! You logged in earlier today."
        logger.debug(
            f"[UPDATE LOGIN STREAK] Profile {profile.id} already logged in today. No update needed."
        )
    elif profile.last_login.date() == today - timedelta(days=1):
        profile.login_streak += 1  # Continue the streak
        message_text = f"Welcome back! You logged in yesterday. Your login streak is now {profile.login_streak} days."
        logger.debug(
            f"[UPDATE LOGIN STREAK] Profile {profile.id} logged in two days in a row."
        )
    else:
        profile.login_streak = 1  # Reset streak
        message_text = f"Welcome back, we missed you! Your login streak has been reset."
        logger.debug(
            f"[UPDATE LOGIN STREAK] Profile {profile.id} missed a day. Resetting login streak."
        )

    if profile.login_streak_max < profile.login_streak:
        profile.login_streak_max = profile.login_streak
        logger.debug(
            f"[UPDATE LOGIN STREAK] Profile {profile.id} has a new max login streak: {profile.login_streak_max}"
        )

    ServerMessage.objects.create(
        group=profile.group_name,
        type="notification",
        action="notification",
        data={},
        message=message_text,
        is_draft=False,
    )

    profile.last_login = timezone.now()
    profile.total_logins += 1
    profile.save()
    logger.debug(
        f"[UPDATE LOGIN STREAK] Updated login streak for profile {profile.id}: {profile.login_streak}"
    )
