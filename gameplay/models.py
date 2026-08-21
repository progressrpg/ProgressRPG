"""
Models for the gameplay application, including timers and server messages.
These models are used to manage in-game logic, track player progress, and
handle rewards.

Author: Duncan Appleby
"""

# gameplay.models
from datetime import timedelta

from django.db import models, transaction
from django.utils import timezone
from typing import TYPE_CHECKING
import json, logging

from progression.models import PlayerActivity

logger = logging.getLogger("general")


class Currency(models.Model):
    code = models.SlugField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    symbol = models.CharField(max_length=10, blank=True)
    precision = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["code"]

    def __str__(self):
        return self.name


class CurrencyAccountBase(models.Model):
    earned = models.PositiveIntegerField(default=0)
    spent = models.PositiveIntegerField(default=0)
    last_calculated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True

    @property
    def balance(self):
        return self.earned - self.spent

    @transaction.atomic
    def spend(self, amount: int):
        if amount < 0:
            raise ValueError("Amount must be non-negative")
        if amount > self.balance:
            raise ValueError("Cannot spend more than the current balance")
        self.spent += amount
        self.last_calculated_at = timezone.now()
        self.save(update_fields=["spent", "last_calculated_at"])

    @transaction.atomic
    def earn(self, amount: int):
        if amount < 0:
            raise ValueError("Amount must be non-negative")
        self.earned += amount
        self.last_calculated_at = timezone.now()
        self.save(update_fields=["earned", "last_calculated_at"])


class Timer(models.Model):
    """
    An abstract base model that represents a general timer for activities
    such as quests or projects.
    """

    start_time = models.DateTimeField(null=True, blank=True)
    elapsed_time = models.PositiveIntegerField(default=0)  # Time in seconds
    created_at = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    STATUS_CHOICES = [
        ("active", "Active"),
        ("paused", "Paused"),
        ("waiting", "Waiting"),
        ("completed", "Completed"),
        ("empty", "Empty"),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="empty")

    if TYPE_CHECKING:
        # Django adds this implicit PK on concrete subclasses; not visible
        # on the abstract base itself.
        id: int

    class Meta:
        abstract = True

    def get_elapsed_time(self):
        if self.start_time and self.status == "active":
            logger.debug(
                f"[GET ELAPSED] Timer {self.id} active — start_time: {self.start_time}, now: {timezone.now()}, base: {self.elapsed_time}"
            )
            return (
                int((timezone.now() - self.start_time).total_seconds())
                + self.elapsed_time
            )
        logger.debug(
            f"[GET ELAPSED] Timer {self.id} status: '{self.status}' and start time: '{self.start_time}' — returning stored elapsed_time: {self.elapsed_time}"
        )
        return self.elapsed_time

    def compute_elapsed(self):
        """Calculate time without updating the model."""
        return self.get_elapsed_time()

    def apply_elapsed(self):
        """Store current elapsed time in the DB."""
        self.elapsed_time = self.get_elapsed_time()
        logger.debug(
            f"[APPLY ELAPSED] Timer {self.id} — elapsed_time set to {self.elapsed_time}"
        )
        self.start_time = None
        self.save()
        return self

    def start(self):
        """
        Start the timer and set its status to 'active'.
        """
        logger.debug(
            f"[TIMER START DEBUG] Timer {self.id} status before: {self.status}, after: active, time: {timezone.now()}"
        )

        if self.status != "active":
            self.status = "active"
            self.start_time = timezone.now()
            self.save(update_fields=["status", "start_time"])
            logger.debug(f"[TIMER START] Timer {self.id} started at {self.start_time}")
        return self

    def pause(self):
        """
        Pause the timer and update its elapsed time.
        """
        if self.status != "paused":
            self.apply_elapsed()
            self.status = "paused"
            self.save(update_fields=["status"])
        return self

    def set_waiting(self):
        """
        Set the timer status to 'waiting'.
        """
        if self.status != "waiting":
            self.status = "waiting"
            self.save(update_fields=["status"])
        return self

    def complete(self):
        """
        Mark the timer as 'completed' and update its elapsed time.
        """
        logger.debug(
            f"[COMPLETE DEBUG] Timer {self.id} — status: {self.status}, start_time: {self.start_time}, elapsed_time before: {self.elapsed_time}"
        )

        if self.status != "completed":
            self.apply_elapsed()
            self.status = "completed"
            self.save()
        return self

    def reset(self):
        """
        Reset the timer, clearing all elapsed time and setting status to 'empty'.
        """
        if self.status != "empty":
            self.status = "empty"
            self.elapsed_time = 0
            self.start_time = None
            self._reset_hook()
            self.save(update_fields=["status", "elapsed_time", "start_time"])
        return self

    def _reset_hook(self):
        pass

    def is_active(self):
        """
        Check if the timer is currently active.

        :return: True if the timer is active, False otherwise.
        :rtype: bool
        """
        return self.status == "active"


class ActivityTimer(Timer):
    """
    A timer that tracks progress on player activities.

    """

    player = models.OneToOneField(
        "users.Player", on_delete=models.CASCADE, related_name="activity_timer"
    )
    activity = models.ForeignKey(
        "progression.PlayerActivity",
        on_delete=models.SET_NULL,
        related_name="activity_timer",
        null=True,
        blank=True,
    )
    # A declared duration for this session, in seconds. Null means
    # unbounded. Deliberately not called `duration`: TimeRecord.duration
    # means elapsed time, and having two adjacent fields with opposite
    # meanings would fail as a plausible wrong number rather than an error.
    #
    # Persisted rather than held in the browser so the server can honour it:
    # a bounded session has a knowable end, so when the connection drops
    # there is nothing to guess - it runs to that end and completes there,
    # instead of needing a verdict about whether the player is still around.
    limit_seconds = models.PositiveIntegerField(null=True, blank=True)
    limit_reason = models.CharField(max_length=32, blank=True, default="")

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # logger.debug(f"[Activity timer save] Compute elapsed: {self.compute_elapsed()}")

    def __str__(self):
        return f"ActivityTimer {self.id} for {self.player.name}"

    def new_activity(self, name="", task=None, start_immediately=False):
        """
        Assign a new activity to the timer.
        Optionally associate it with a Task.

        `start_immediately` folds the "waiting" step in: rather than landing
        in `waiting` and requiring a separate `start()` call (and its own
        save + broadcast) to actually begin ticking, the timer goes straight
        to `active` in this same save. This is what a fresh "press Start"
        should do — the two-call shape existed only so `label_activity` and
        `resume()` could act on a `waiting`/`paused` timer independently;
        neither of those needs a session to pass through `waiting` first.
        """
        logger.debug(
            f"[ACTIVITYTIMER.new_activity]: Assigning new activity {name} "
            f"(task={getattr(task, 'id', None)}) to timer {self.pk}, "
            f"start_immediately={start_immediately}"
        )

        self.activity = PlayerActivity.objects.create(
            name=name,
            player=self.player,
            task=task,
        )

        self.start_time = timezone.now() if start_immediately else None
        self.elapsed_time = 0
        self.status = "active" if start_immediately else "waiting"
        # A new session inherits nothing from the previous one's declared
        # duration; set_limit() applies the new one (or the free ceiling).
        self.limit_seconds = None
        self.limit_reason = ""

        self.save(
            update_fields=[
                "activity",
                "start_time",
                "elapsed_time",
                "status",
                "limit_seconds",
                "limit_reason",
            ]
        )
        logger.debug(
            f"ActivityTimer after save: {self.pk}, activity: {self.activity}, "
            f"status: {self.status}"
        )
        return self

    def change_task(self, new_task):
        assert self.activity is not None, "change_task requires an assigned activity"
        self.activity.task = new_task
        self.activity.save(update_fields=["task"])
        return self

    def has_banked_time(self) -> bool:
        """Whether this timer is holding time the player hasn't resolved."""
        return self.status == "paused" and self.elapsed_time > 0

    def can_resume(self) -> bool:
        """
        Whether a paused session may still be picked up where it left off.

        Only while its own logical day is current. After that the banked
        time is still the player's - they submit it - but continuing to add
        to it would credit today's work to the day the session began.
        """
        if self.status != "paused":
            return False

        if not self.activity or self.activity.logical_date is None:
            # No day recorded (a session that predates logical dates, or one
            # never properly started): don't strand the player over it.
            return True

        from progression.day_boundaries import current_logical_date

        return self.activity.logical_date == current_logical_date(self.player)

    def is_bounded(self) -> bool:
        """Whether this session declared its own end."""
        return bool(self.limit_seconds)

    def limit_remaining(self) -> int | None:
        """Seconds left before the declared limit, or None if unbounded."""
        if not self.is_bounded():
            return None
        assert self.limit_seconds is not None
        return max(0, self.limit_seconds - self.get_elapsed_time())

    def limit_reached(self) -> bool:
        """Whether a bounded session has run out its declared duration."""
        remaining = self.limit_remaining()
        return remaining is not None and remaining <= 0

    def set_limit(self, limit_seconds, reason: str = "") -> None:
        """
        Apply a declared duration, clamped to the free-tier ceiling for
        non-premium players. The client clamps too, but a limit arriving
        from a client is a claim rather than a fact.
        """
        from core.models import GameSettings

        try:
            parsed = int(limit_seconds)
        except (TypeError, ValueError):
            parsed = 0

        resolved = parsed if parsed > 0 else None
        resolved_reason = reason or ("preset_limit" if resolved else "")

        if not self.player.is_premium:
            ceiling = int(GameSettings.current().free_timer_limit_seconds)
            if ceiling > 0 and (resolved is None or resolved > ceiling):
                resolved = ceiling
                resolved_reason = "free_limit"

        self.limit_seconds = resolved
        self.limit_reason = resolved_reason
        self.save(update_fields=["limit_seconds", "limit_reason"])

    def start(self):
        """
        Start the timer and persist the associated activity start timestamp.
        """
        super().start()

        if self.activity and self.activity.started_at is None:
            from progression.day_boundaries import logical_date_for

            self.activity.started_at = self.start_time or timezone.now()
            # Stamped here, once, so the session keeps the day it began on
            # however many times it is later paused and resumed.
            self.activity.logical_date = logical_date_for(
                self.player, self.activity.started_at
            )
            self.activity.save(update_fields=["started_at", "logical_date"])

        return self

    def pause(self):
        """
        Pause the activity timer and update the associated activity's duration.
        """
        super().pause()
        self.update_activity_time()

    def update_activity_time(self):
        """
        Update the total duration of the associated activity.
        """
        if self.activity:
            self.activity.new_time(self.elapsed_time)
        else:
            logger.info(
                f"[ACTIVITYTIMER.UPDATE_ACTIVITY_TIME] No activity found for timer {self}. Resetting timer."
            )
            self.reset()

    def rename_activity(self, name):
        if self.activity:
            self.activity.rename(name)

    def complete(
        self,
        newName=None,
        client_elapsed_seconds: int | None = None,
        completion_source: str = "manual",
    ):
        """
        Complete the activity timer and return the XP gained for the activity.
        """
        if not self.activity:
            logger.warning(
                f"[COMPLETE] Timer {self.id} has no activity assigned — skipping activity.complete()"
            )
            return {
                "duration_seconds": 0,
                "base_xp": 0,
                "xp_multiplier": 1,
                "mastery_multiplier": 1,
                "xp_gained": 0,
                "skill_xp_gained": 0,
                "level_ups": [],
            }

        if self.status == "completed":
            logger.warning(
                f"[COMPLETE CALLED AGAIN] Timer {self.id} already completed — elapsed_time: {self.elapsed_time}"
            )

        pre_complete_start_time = self.start_time
        super().complete()

        if completion_source == "auto":
            try:
                if client_elapsed_seconds is None:
                    raise TypeError
                parsed_client_elapsed = int(client_elapsed_seconds)
            except (TypeError, ValueError):
                parsed_client_elapsed = None

            if (
                parsed_client_elapsed is not None
                and parsed_client_elapsed > self.elapsed_time
            ):
                self.elapsed_time = parsed_client_elapsed
                self.save(update_fields=["elapsed_time"])

        if newName:
            self.rename_activity(newName)
        self.update_activity_time()

        if self.activity.started_at is None:
            from progression.day_boundaries import logical_date_for

            if pre_complete_start_time is not None:
                backfilled_started_at = pre_complete_start_time
            else:
                backfilled_started_at = timezone.now() - timedelta(
                    seconds=max(0, int(self.elapsed_time))
                )

            self.activity.started_at = backfilled_started_at
            self.activity.logical_date = logical_date_for(
                self.player, backfilled_started_at
            )
            self.activity.save(update_fields=["started_at", "logical_date"])

        reward_summary = self.activity.get_xp_reward_summary()
        xp_gained = self.activity.complete(reward_summary=reward_summary)
        level_ups = self.player.add_activity(self.elapsed_time, xp=xp_gained)

        from progression.daily_goals import check_and_award_daily_goals

        # Against the session's own logical day rather than the current one:
        # a session started before the day rolled over completes the goals
        # for the day it was worked, however late it is submitted.
        goals_state, bonus_level_ups = check_and_award_daily_goals(
            self.player, today=self.activity.logical_date
        )
        level_ups = level_ups + bonus_level_ups

        reward_summary["level_ups"] = level_ups
        reward_summary["daily_goals_bonus_ap"] = goals_state.bonus_ap

        logger.debug(
            f"[TIMER COMPLETE] Timer {self.id} completed — elapsed_time: {self.elapsed_time}, completed_at: {self.activity.completed_at}"
        )

        self.reset()

        return reward_summary

    def _reset_hook(self):
        self.activity = None
        self.limit_seconds = None
        self.limit_reason = ""

    def reset(self):
        """
        Reset the activity timer and dissociate the current activity.
        """
        super().reset()
        self.activity = None
        self.save()


class ServerMessage(models.Model):
    """
    Represents a message sent by the server to a specific user player. This
    can be used for notifications, responses, or event-driven communication.

    """

    group = models.CharField(
        max_length=50, help_text="WebSocket group to send this message to."
    )
    type = models.CharField(
        max_length=20,
        choices=[
            ("event", "Event"),
            ("server_message", "Server Message"),
            ("action", "Action"),
            ("response", "Response"),
            ("error", "Error"),
            ("notification", "Notification"),
        ],
    )
    action = models.CharField(
        max_length=50
    )  # e.g., 'quest_complete', 'reward', 'message'
    data = models.JSONField(blank=True, null=True)  # Store event-specific data as JSON
    message = models.TextField(max_length=2000, blank=True, null=True)
    is_delivered = models.BooleanField(default=False)  # Track delivery status
    created_at = models.DateTimeField(
        auto_now_add=True
    )  # Timestamp for when it was queued
    is_draft = models.BooleanField(default=True)

    def to_dict(self):
        """
        Convert the server message to a dictionary representation.

        """
        message = {
            "type": self.type,
            "data": self.data,
            "action": self.action,
            "message": self.message,
            "created_at": self.created_at.isoformat(),
        }
        return message

    def to_json(self):
        """
        Convert the server message to a JSON string for sending over WebSocket.

        """
        return json.dumps(self.to_dict())

    def mark_delivered(self):
        """
        Mark the server message as delivered and update its status in the database.
        """
        self.is_delivered = True
        self.save(update_fields=["is_delivered"])

    def __str__(self):
        return f"{self.type.upper()} - {self.action} ({'Delivered' if self.is_delivered else 'Pending'})"

    @classmethod
    def get_unread(cls, group_name):
        """
        Fetch all undelivered server messages for a specific WebSocket group.

        """
        return cls.objects.filter(group=group_name, is_delivered=False)

    @classmethod
    def clear_old(cls, days=30):
        """
        Delete server messages that are older than the specified number of days.

        """
        cutoff_date = timezone.now() - timedelta(days=days)
        cls.objects.filter(created_at__lt=cutoff_date).delete()


class XpModifier(models.Model):
    class Scope(models.TextChoices):
        PLAYER = "PLAYER", "Player"
        CHARACTER = "CHARACTER", "Character"

    scope = models.CharField(max_length=20, choices=Scope.choices)
    player = models.ForeignKey(
        "users.Player",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="xp_mods",
    )
    character = models.ForeignKey(
        "character.Character",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="xp_mods",
    )

    key = models.CharField(
        max_length=64
    )  # e.g. "player_online", "focus_streak", "event_weekend"
    multiplier = models.DecimalField(max_digits=6, decimal_places=3, default=1.0)

    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField(null=True, blank=True)  # null = indefinite
    is_active = models.BooleanField(default=True)

    task_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Optional Celery task ID for scheduled end task.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["key", "is_active", "starts_at", "ends_at"]),
        ]
