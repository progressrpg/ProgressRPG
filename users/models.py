"""
User Management Models

This module contains the models and custom manager for handling user-related data in the application.
It includes a custom user model for email-based authentication, an abstract base model for shared
attributes, and a profile model for tracking gameplay-specific details.

Classes:
    - CustomUserManager: A custom manager to handle the creation of users and superusers.
    - CustomUser: A custom user model extending Django's AbstractUser with email-based login.
    - Person: An abstract base model for characters or profiles, tracking levels, XP, and buffs.
    - Profile: A concrete model for user profiles, extending the Person model to add gameplay-specific
      attributes like activities, streaks, and buffs.

Usage:
These models are central to managing user authentication and gameplay profiles in the application.
CustomUser enables email-based login, while Profile tracks user-specific gameplay progress, subscriptions,
and linked characters.

Author:
    Duncan Appleby

"""

from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models, transaction
from django.utils import timezone
from typing import TYPE_CHECKING, Optional
import logging

1
from gameplay.models import ServerMessage

if TYPE_CHECKING:
    from character.models import Character

logger = logging.getLogger("django")


# class CustomUserManager(BaseUserManager):
class CustomUserManager(UserManager["CustomUser"]):
    """
    Custom manager for `CustomUser` model to handle user creation.

    Methods:
        create_user: Creates and returns a regular user with an email and password.
        create_superuser: Creates and returns a superuser with elevated permissions.
    """

    @transaction.atomic
    def create_user(
        self, email: Optional[str], password: Optional[str], **extra_fields
    ):
        """
        Create and return a regular user with an email and password.
        """
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        extra_fields.setdefault("is_active", True)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    @transaction.atomic
    def create_superuser(
        self, email: Optional[str], password: Optional[str], **extra_fields
    ):
        """
        Create and return a superuser with elevated permissions.
        """
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra_fields)


class CustomUser(AbstractUser):
    """
    Custom user model extending Django's AbstractUser.
    """

    username = None
    email = models.EmailField(unique=True)
    date_of_birth = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    objects = CustomUserManager()
    pending_delete = models.BooleanField(default=False)
    delete_at = models.DateTimeField(null=True, blank=True)
    is_confirmed = models.BooleanField(default=False)

    EMAIL_FIELD = "email"
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email


class Person(models.Model):
    """
    An abstract base model representing a generic person with levels, XP, and buffs.
    """

    name = models.CharField(max_length=100, blank=True, null=True)
    xp = models.PositiveIntegerField(default=0)
    xp_next_level = models.PositiveIntegerField(default=0)
    xp_modifier = models.FloatField(default=1)
    level = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True

    @transaction.atomic
    def add_xp(self, amount: int):
        """
        Add experience points (XP) to the person and handle level-up logic.
        """
        self.xp += amount
        levelups = []

        while self.xp >= self.get_xp_for_next_level():
            old_level = self.level
            self.level_up()
            levelups.append(
                {
                    "old_level": old_level,
                    "new_level": self.level,
                    "person": self,
                    "name": self.name,
                }
            )
            self.xp_next_level = self.get_xp_for_next_level()
        self.save(update_fields=["xp_next_level", "xp"])

        return levelups

    def level_up(self):
        """
        Increase the level of the person and reset XP accordingly.
        """
        self.xp -= self.get_xp_for_next_level()
        self.level += 1
        self.save(update_fields=["level", "xp"])

    def get_xp_for_next_level(self):
        """
        Calculate the XP required to reach the next level.
        """
        return 100 * (self.level + 1) if self.level >= 1 else 100

    def apply_buffs(self, base_value: Optional[int], attribute: Optional[str]) -> int:
        """
        Apply active buffs to a given attribute (e.g., 'xp').
        """
        total_value = base_value
        for buff in self.buffs.filter(attribute=attribute):
            total_value = buff.calc_value(total_value)
        return int(total_value)

    def clear_expired_buffs(self):
        """Remove expired buffs from person."""
        # Not working
        # timedelta_duration = ExpressionWrapper(F('duration'), output_field=fields.DurationField())
        # self.buffs.filter(created_at__lt=now() - timedelta_duration).delete()


class Profile(Person):
    """
    Represents a user's gameplay profile, extending the abstract Person model.
    Tracks user-specific gameplay data such as total activities, buffs, and characters.
    """

    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    bio = models.TextField(max_length=1000, blank=True)
    total_time = models.IntegerField(default=0)
    total_activities = models.IntegerField(default=0)
    is_premium = models.BooleanField(default=False)
    is_online = models.BooleanField(default=False)
    last_login = models.DateTimeField(default=timezone.now, null=True, blank=True)
    login_streak = models.PositiveIntegerField(default=1)
    login_streak_max = models.PositiveIntegerField(default=1)
    total_logins = models.PositiveIntegerField(default=0)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    buffs = models.ManyToManyField(
        "gameplay.AppliedBuff", related_name="profiles", blank=True
    )

    ONBOARDING_STEPS = [
        (0, "Not started"),
        (1, "Step 1: Profile creation"),
        (2, "Step 2: Character generation"),
        (3, "Step 3: Subscription"),
        (4, "Completed"),
    ]
    onboarding_step = models.PositiveIntegerField(choices=ONBOARDING_STEPS, default=0)

    @property
    def needs_onboarding(self):
        return self.onboarding_step < 4

    @property
    def group_name(self):
        """Returns the WebSocket group name for this profile."""
        return f"profile_{self.id}"

    def set_online(self):
        """Marks profile as online."""
        logger.debug("[SET ONLINE] Running set_online for profile")
        self.is_online = True
        self.save(update_fields=["is_online"])

    def set_offline(self):
        """Marks profile as offline."""
        self.is_online = False
        self.save(update_fields=["is_online"])

    @classmethod
    def get_online_profiles(cls):
        """Returns a QuerySet of all currently online profiles."""
        return cls.objects.filter(is_online=True)

    @property
    def current_character(self):
        """
        Retrieve the active character associated with this profile.
        """
        from character.models import PlayerCharacterLink

        return PlayerCharacterLink.get_character(self)

    def __str__(self):
        return self.name if self.name else "Unnamed profile"

    def add_activity(self, time: int = 0, num: int = 1, xp: int = 0):
        """
        Update the total time and number of activities for this profile.
        """
        self.total_time += time
        self.total_activities += num

        levelups = []
        if xp:
            levelups = self.add_xp(xp)
        self.save(update_fields=["total_time", "total_activities"])

        for event in levelups:
            ServerMessage.objects.create(
                group=self.group_name,
                type="notification",
                action="notification",
                message=f"{self.name} levelled up! Now level {event['new_level']}.",
                data={"level": event["new_level"]},
                is_draft=False,
            )

    def change_character(self, new_character: "Character"):
        """
        Switch the profile's active character to a new character.
        """
        from character.models import PlayerCharacterLink

        old_link = PlayerCharacterLink.objects.filter(
            profile=self, is_active=True
        ).first()
        if old_link:
            old_link.unlink()

        PlayerCharacterLink.objects.create(profile=self, character=new_character)
        self.save()


class InviteCode(models.Model):
    code = models.CharField(max_length=50, unique=True)
    is_active = models.BooleanField(default=True)
    max_uses = models.PositiveIntegerField(null=True, blank=True)
    uses = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    def is_valid(self):
        if not self.is_active:
            return False
        if self.expires_at and timezone.now() > self.expires_at:
            return False
        if self.max_uses and self.uses >= self.max_uses:
            return False
        return True

    def use(self):
        self.uses += 1
        if self.max_uses and self.uses >= self.max_uses:
            self.is_active = False
        self.save()

    def __str__(self):
        return self.code
