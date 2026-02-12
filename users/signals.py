# user.signals
from allauth.account.signals import email_confirmed
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver
import logging

from .models import UserLogin, Player
from .utils import assign_character_to_player

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


@receiver(post_save, sender=UserLogin)
def handle_first_login(sender, instance: UserLogin, created, **kwargs):
    if created and instance.is_first_login_of_day():
        from users.services.login_services import handle_first_login_of_day

        handle_first_login_of_day(instance.user)
