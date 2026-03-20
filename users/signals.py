# user.signals
from allauth.account.signals import email_confirmed
from django.contrib.auth import get_user_model
from django.contrib.auth.signals import user_logged_in
from django.db.models.signals import post_save
from django.dispatch import receiver
import logging

from .models import Player, UserLogin
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
        Player.objects.get_or_create(user=instance)


@receiver(post_save, sender=Player)
def assign_character(sender, instance, created, raw=False, **kwargs):
    """Assign character when player created"""
    if raw:
        return
    if created:
        assign_character_to_player(instance)


@receiver(user_logged_in)
def record_login_event(sender, request, user, **kwargs):
    if request.path.startswith("/admin/"):
        return

    UserLogin.objects.create(user=user)


@receiver(post_save, sender=UserLogin)
def handle_first_login(sender, instance, created, raw=False, **kwargs):
    if raw or not created or not instance.is_first_login_of_day():
        return

    from users.services.login_services import handle_first_login_of_day

    handle_first_login_of_day(instance.user)
