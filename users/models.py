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

from datetime import timedelta
from decimal import Decimal
from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models, transaction
from django.db.models import Sum
from django.utils import timezone
from typing import TYPE_CHECKING, Optional
import logging
from timezone_field import TimeZoneField

from gameplay.models import Currency, CurrencyAccountBase, ServerMessage

if TYPE_CHECKING:
    from character.models import Character

logger = logging.getLogger("general")


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
    timezone = TimeZoneField(default="UTC")
    created_at = models.DateTimeField(auto_now_add=True)
    objects = CustomUserManager()
    pending_delete = models.BooleanField(default=False)
    delete_at = models.DateTimeField(null=True, blank=True)
    is_confirmed = models.BooleanField(default=False)
    stripe_customer_id = models.CharField(
        max_length=255, blank=True, null=True, unique=True
    )

    EMAIL_FIELD = "email"
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    @property
    def days_logged_in(self):
        return UserLogin.days_logged_in(self)

    @property
    def current_login_streak(self):
        return UserLogin.current_login_streak(self)

    @property
    def max_login_streak(self):
        return UserLogin.max_login_streak(self)

    @property
    def total_login_events(self):
        return UserLogin.total_login_events(self)

    @property
    def last_recorded_login(self):
        return UserLogin.last_recorded_login(self)

    @property
    def is_premium(self):
        from payments.models import UserSubscription

        subscription = UserSubscription.current_for_user(self)
        if not subscription:
            return False
        return subscription.is_active_premium

    def __str__(self):
        return self.email


class UserLogin(models.Model):
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="logins",
    )
    timestamp = models.DateTimeField(auto_now_add=True)

    def local_date(self):
        return timezone.localtime(self.timestamp).date()

    def is_first_login_of_day(self):
        today = self.local_date()
        previous_logins_today = UserLogin.objects.filter(
            user=self.user,
            timestamp__date=today,
            timestamp__lt=self.timestamp,
        )
        return not previous_logins_today.exists()

    @classmethod
    def total_login_events(cls, user):
        return cls.objects.filter(user=user).count()

    @classmethod
    def days_logged_in(cls, user):
        login_dates = {
            login.local_date()
            for login in cls.objects.filter(user=user).only("timestamp")
        }
        return len(login_dates)

    @classmethod
    def last_recorded_login(cls, user):
        last = cls.objects.filter(user=user).order_by("-timestamp").first()
        return last.timestamp if last else None

    @classmethod
    def current_login_streak(cls, user):
        login_dates = sorted(
            {
                login.local_date()
                for login in cls.objects.filter(user=user).only("timestamp")
            },
            reverse=True,
        )
        if not login_dates:
            return 0

        streak = 0
        day = timezone.localdate()
        login_dates_set = set(login_dates)
        while day in login_dates_set:
            streak += 1
            day -= timedelta(days=1)
        return streak

    @classmethod
    def max_login_streak(cls, user):
        login_dates = sorted(
            {
                login.local_date()
                for login in cls.objects.filter(user=user).only("timestamp")
            }
        )
        if not login_dates:
            return 0

        max_streak = 1
        current_streak = 1
        for idx in range(1, len(login_dates)):
            if login_dates[idx] == login_dates[idx - 1] + timedelta(days=1):
                current_streak += 1
            else:
                current_streak = 1
            max_streak = max(max_streak, current_streak)
        return max_streak

    def __str__(self):
        return f"{self.user.email} @ {self.timestamp.isoformat()}"


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
    is_online = models.BooleanField(default=False)
    active_connections = models.PositiveIntegerField(default=0)
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
    def needs_onboarding(self):
        return self.onboarding_step < 2

    @property
    def is_premium(self):
        return self.user.is_premium

    @property
    def group_name(self):
        """Returns the WebSocket group name for this player."""
        return f"player_{self.id}"

    def get_currency(self, code="link_points") -> "PlayerCurrency":
        currency_def, _ = Currency.objects.get_or_create(
            code=code,
            defaults={"name": code.replace("_", " ").title()},
        )
        currency, _ = self.currencies.get_or_create(currency=currency_def)
        return currency

    def set_online(self):
        """Marks player as online."""
        logger.debug("[SET ONLINE] Running set_online for player")
        self.is_online = True
        self.save(update_fields=["is_online"])

    def set_offline(self):
        """Marks player as offline."""
        self.is_online = False
        self.save(update_fields=["is_online"])

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


class PlayerCurrency(CurrencyAccountBase):
    player = models.ForeignKey(
        Player,
        on_delete=models.CASCADE,
        related_name="currencies",
    )
    currency = models.ForeignKey(
        Currency,
        on_delete=models.CASCADE,
        related_name="player_accounts",
    )

    class Meta:
        unique_together = ("player", "currency")
