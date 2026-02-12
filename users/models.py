"""
User Management Models

This module contains the models and custom manager for handling user-related data in the application.
It includes a custom user model for email-based authentication, an abstract base model for shared
attributes, and a player model for tracking gameplay-specific details.

Classes:
    - CustomUserManager: A custom manager to handle the creation of users and superusers.
    - CustomUser: A custom user model extending Django's AbstractUser with email-based login.
    - Person: An abstract base model for characters or players, tracking levels and XP.
    - Player: A concrete model for user players, extending the Person model to add gameplay-specific
      attributes like activities and streaks.

Usage:
These models are central to managing user authentication and gameplay players in the application.
CustomUser enables email-based login, while Player tracks user-specific gameplay progress, subscriptions,
and linked characters.

Author:
    Duncan Appleby

"""

from decimal import Decimal
from django.conf import settings
from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models, transaction
from django.db.models import Sum
from django.utils import timezone
from typing import TYPE_CHECKING, Optional
import logging

from gameplay.models import ServerMessage
import users.services.login_services as login_services

if TYPE_CHECKING:
    from character.models import Character

logger = logging.getLogger("general")


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

    stripe_customer_id = models.CharField(max_length=255, blank=True, null=True)
    stripe_subscription_id = models.CharField(max_length=255, blank=True, null=True)
    subscription_status = models.CharField(max_length=50, blank=True, null=True)
    subscription_current_period_end = models.DateTimeField(blank=True, null=True)
    current_price_id = models.CharField(max_length=255, blank=True, null=True)

    EMAIL_FIELD = "email"
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    @property
    def has_premium_subscription(self):
        return (
            self.subscription_status == "active"
            and self.current_price_id == settings.STRIPE_PREMIUM_MONTHLY_PRICE_ID
        )

    @property
    def days_logged_in(self):
        return UserLogin.days_logged_in(self)

    @property
    def last_login(self):
        return UserLogin.last_login(self)

    @property
    def current_login_streak(self):
        return UserLogin.current_login_streak(self)

    @property
    def max_login_streak(self):
        return UserLogin.max_login_streak(self)

    def __str__(self):
        return self.email


class UserLogin(models.Model):
    """
    Model to track user login timestamps for streak calculations.
    """

    user = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name="logins"
    )
    timestamp = models.DateTimeField(auto_now_add=True)

    def local_date(self):
        """Return the date of this login in local timezone."""
        return self.timestamp.astimezone(timezone.get_current_timezone()).date()

    def is_first_login_of_day(self):
        """Check if this is the first login today for this user."""
        today = self.local_date()
        # Any logins earlier today?
        previous_logins_today = UserLogin.objects.filter(
            user=self.user, timestamp__date=today, timestamp__lt=self.timestamp
        )
        return not previous_logins_today.exists()

    @classmethod
    def days_logged_in(cls, user):
        """Number of unique days the user has logged in."""
        login_dates = {
            login.timestamp.astimezone(timezone.get_current_timezone()).date()
            for login in cls.objects.filter(user=user)
        }
        return len(login_dates)

    @classmethod
    def last_login(cls, user):
        """Most recent login timestamp."""
        last = cls.objects.filter(user=user).order_by("-timestamp").first()
        return last.timestamp if last else None

    @classmethod
    def current_login_streak(cls, user):
        """Current consecutive-day login streak, including today."""
        login_dates = sorted(
            {
                login.timestamp.astimezone(timezone.get_current_timezone()).date()
                for login in cls.objects.filter(user=user)
            },
            reverse=True,
        )
        if not login_dates:
            return 0
        return login_services.current_login_streak(cls, login_dates)

    @classmethod
    def max_login_streak(cls, user):
        """Maximum consecutive-day login streak ever."""
        login_dates = sorted(
            {
                login.timestamp.astimezone(timezone.get_current_timezone()).date()
                for login in cls.objects.filter(user=user)
            }
        )
        if not login_dates:
            return 0
        return login_services.max_login_streak(cls, login_dates)


class Person(models.Model):
    """
    An abstract base model representing a generic person with levels and XP.
    """

    name = models.CharField(max_length=100, blank=True, null=True)
    xp = models.PositiveIntegerField(default=0)
    xp_next_level = models.PositiveIntegerField(default=100)
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

        while True:
            xp_needed = self.get_xp_for_next_level()
            if self.xp < xp_needed:
                break

            old_level = self.level
            self.xp -= xp_needed
            self.level += 1
            levelups.append(
                {
                    "old_level": old_level,
                    "new_level": self.level,
                    "person": self,
                    "name": self.name,
                }
            )

        self.xp = max(0, self.xp)
        self.xp_next_level = self.get_xp_for_next_level()

        self.save(update_fields=["xp", "level", "xp_next_level"])
        return levelups

    def get_xp_for_next_level(self):
        """
        Calculate the XP required to reach the next level.
        """
        return 100 * (self.level + 1) if self.level >= 1 else 100

    def get_xp_multiplier(self, now=None):
        now = now or timezone.now()

        link = self.active_link

        mods = self.xp_mods.filter(
            is_active=True,
            starts_at__lte=now,
        ).filter(models.Q(ends_at__isnull=True) | models.Q(ends_at__gt=now))
        mult = Decimal("1.0")
        for m in mods:
            mult *= m.multiplier

        return mult


class Player(Person):
    """
    Represents a user's gameplay player, extending the abstract Person model.
    Tracks user-specific gameplay data such as total activities and characters.
    """

    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    bio = models.TextField(max_length=1000, blank=True)
    active_connections = models.PositiveIntegerField(default=0)
    is_online = models.BooleanField(default=False)
    last_seen = models.DateTimeField(null=True, blank=True)

    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    ONBOARDING_STEPS = [
        (0, "Not started"),
        (1, "Step 1: Player creation"),
        (2, "Completed"),
    ]
    onboarding_step = models.PositiveIntegerField(choices=ONBOARDING_STEPS, default=0)

    onboarding_completed = models.BooleanField(default=False)
    # onboarding = models.JSONField(default=dict, blank=True)

    @property
    def is_premium(self):
        return self.user.has_premium_subscription

    @property
    def needs_onboarding(self):
        return self.onboarding_step < 2

    @property
    def group_name(self):
        """Returns the WebSocket group name for this player."""
        return f"player_{self.id}"

    def get_currency(self, name="link_points") -> "PlayerCurrency":
        currency, _ = self.currencies.get_or_create(name=name)
        return currency

    def increment_connection(self):
        self.active_connections += 1
        self.is_online = True
        self.save(update_fields=["active_connections", "is_online"])

    def decrement_connection(self):
        if self.active_connections > 0:
            self.active_connections -= 1
        self.save(update_fields=["active_connections"])

    def connect(self):
        self.active_connections += 1
        if not self.is_online:
            self.is_online = True
        self.save(update_fields=["active_connections", "is_online"])
        return self.is_online

    def disconnect(self):
        if self.active_connections == 0:
            self.is_online = False
            self.last_seen = timezone.now()
            self.save(update_fields=["active_connections", "is_online", "last_seen"])

    @classmethod
    def get_online_players(cls):
        """Returns a QuerySet of all currently online players."""
        return cls.objects.filter(is_online=True)

    @property
    def active_link(self):
        from character.models import PlayerCharacterLink

        return PlayerCharacterLink.objects.filter(player=self, is_active=True).first()

    @property
    def current_character(self):
        """
        Retrieve the active character associated with this player.
        """
        from character.models import PlayerCharacterLink

        return PlayerCharacterLink.get_character(self)

    def __str__(self):
        return self.name if self.name else "Unnamed player"

    @property
    def total_time(self):
        return (
            self.activities.filter(is_complete=True).aggregate(total=Sum("duration"))[
                "total"
            ]
            or 0
        )

    @property
    def total_activities(self):
        return self.activities.filter(is_complete=True).count()

    def add_activity(self, time: int = 0, num: int = 1, xp: int = 0):
        """
        Apply XP rewards for a completed activity.
        """
        levelups = []
        if xp:
            levelups = self.add_xp(xp)

        for event in levelups:
            ServerMessage.objects.create(
                group=self.group_name,
                type="notification",
                action="notification",
                message=f"You levelled up! Now level {event['new_level']}.",
                data={"level": event["new_level"]},
                is_draft=False,
            )

    def change_character(self, new_character: "Character"):
        """
        Switch the player's active character to a new character.
        """
        from character.models import PlayerCharacterLink

        old_link = PlayerCharacterLink.objects.filter(
            player=self, is_active=True
        ).first()
        if old_link:
            old_link.unlink()

        PlayerCharacterLink.objects.create(player=self, character=new_character)
        self.save()


class PlayerCurrency(models.Model):
    player = models.ForeignKey(
        Player, on_delete=models.CASCADE, related_name="currencies"
    )
    name = models.CharField(max_length=50)
    earned = models.PositiveIntegerField(default=0)
    spent = models.PositiveIntegerField(default=0)
    last_calculated_at = models.DateTimeField(null=True, blank=True)

    @property
    def balance(self):
        return self.earned - self.spent

    def spend(self, amount: int):
        if amount > self.balance:
            raise ValueError("Cannot spend more than the current balance")
        self.spent += amount
        self.save(update_fields=["spent"])

    def earn(self, amount: int):
        self.earned += amount
        self.last_calculated_at = timezone.now()
        self.save(update_fields=["earned", "last"])

    class Meta:
        unique_together = ("player", "name")


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
        self.save(update_fields=["uses", "is_active"])

    def __str__(self):
        return self.code
