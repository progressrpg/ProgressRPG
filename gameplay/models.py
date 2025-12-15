"""
Models for the gameplay application, including quests, requirements, completions,
timers, and server messages. These models are used to manage in-game
logic, track player progress, and handle rewards and buffs.

Author: Duncan Appleby
"""

# gameplay.models
from abc import ABC, abstractmethod

# from django_stubs_ext.db.models import Related
from django.db import models, transaction

# from django.db.models import ForeignKey
from django.db.models import QuerySet
from django.utils import timezone
from typing import Optional, Iterable, Dict, Any, cast, List, TYPE_CHECKING
import json, logging, math

from progression.models import CharacterQuest

if TYPE_CHECKING:
    from character.models import Character

logger = logging.getLogger("django")


class Quest(models.Model):
    """
    Represents a quest in the game, with eligibility criteria, duration, and category.

    """

    name = models.CharField(max_length=255)
    description = models.TextField(max_length=2000, blank=True)
    intro_text = models.TextField(max_length=2000, blank=True)
    outro_text = models.TextField(max_length=2000, blank=True)

    def default_duration_choices():
        return [300 * i for i in range(1, 7)]

    duration_choices: Any = models.JSONField(default=default_duration_choices)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    start_date = models.DateTimeField(blank=True, null=True)
    end_date = models.DateTimeField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    stages: Any = models.JSONField(default=list)
    stagesFixed = models.BooleanField(
        default=False, help_text="True if stages must appear in a certain order."
    )

    class Category(models.TextChoices):
        NONE = "NONE", "No category"
        TRADE = "TRADE", "Trade"
        RECUR = "RECUR", "Recurring"
        EVENT = "EVENT", "Event"

    category = models.CharField(max_length=20, default=Category.NONE)
    results: Optional["QuestResults"] = None

    # Eligibility criteria
    is_premium = models.BooleanField(default=False)
    is_task_support = models.BooleanField(default=False)
    levelMin = models.IntegerField(default=0)
    levelMax = models.IntegerField(default=0)
    canRepeat = models.BooleanField(default=True)
    quest_requirements: QuerySet["QuestRequirement"]
    quest_completions: QuerySet["QuestCompletion"]

    class Frequency(models.TextChoices):
        NONE = "NONE", "No limit"
        DAILY = "DAY", "Daily"
        WEEKLY = "WEEK", "Weekly"
        MONTHLY = "MONTH", "Monthly"

    frequency = models.CharField(
        max_length=6, choices=Frequency.choices, default=Frequency.NONE
    )

    def __str__(self):
        return self.name

    def list_requirements(self) -> Iterable["QuestRequirement"]:
        return self.quest_requirements.all()

    def apply_results(self, character: "Character"):
        """
        Apply the results and rewards of the quest to the specified character.

        """
        if self.results:
            self.results.apply(character)
            character.save()

    def requirements_met(self, completed_quests):
        """
        Checks if the character meets all prerequisites for the quest.

        """
        # print("you have arrived in requirements_met")
        if hasattr(self, "quest_requirements"):
            for requirement in self.list_requirements():
                completed_count = completed_quests.get(requirement.prerequisite, 0)
                if completed_count < requirement.times_required:
                    return False
            return True

    def not_repeating(self, character: "Character") -> bool:
        """
        Verify whether the quest can be repeated for the given character.

        """
        # print("you have arrived in not_repeating")
        if hasattr(self, "quest_completions"):
            completions = self.quest_completions.all()
            # Check repeating
            if self.canRepeat == False:
                for completion in completions:
                    if completion.character == character:
                        if completion.times_completed >= 1:
                            return False
            return True

    def frequency_eligible(self, character: "Character"):
        """
        Check if the quest is eligible to be undertaken based on its frequency.

        """
        if self.frequency != "NONE":
            today = timezone.now()
            completions = self.quest_completions.all()
            for completion in completions:
                if completion.character == character:
                    lastCompleted = completion.last_completed

                    if self.frequency == "DAY":
                        if (today - lastCompleted).days == 0:
                            return False

                    elif self.frequency == "WEEK":
                        dateDiff = today - lastCompleted
                        if dateDiff.days < 7:
                            if today.weekday() >= lastCompleted.weekday():
                                return False

                    elif self.frequency == "MONTH":
                        dateDiff = today - lastCompleted
                        if dateDiff.days < 31:
                            todayDate = int(today.strftime("%d"))
                            lastCompletedDate = int(lastCompleted.strftime("%d"))
                            if todayDate >= lastCompletedDate:
                                return False
        return True

    def checkEligible(self, character: "Character", profile):
        """
        Determine if the quest is eligible for the given character and profile.

        """
        # Simple comparison checks
        if not self.is_active:
            return False
        # elif self.is_task_support:
        #    return False
        elif character.level < self.levelMin or character.level > self.levelMax:
            return False
        elif profile.is_premium and self.is_premium:
            return False

        # Quest passed the test
        return True


class QuestResults(models.Model):
    """
    Stores the results and rewards for a quest, including experience points,
    coins, and buffs.

    """

    quest = models.OneToOneField(
        "Quest", on_delete=models.CASCADE, related_name="results"
    )
    dynamic_rewards = models.JSONField(default=dict, null=True, blank=True)
    xp_rate = models.IntegerField(default=1)
    coin_reward = models.IntegerField(default=0)
    buffs = models.JSONField(default=list, blank=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Quest results for Quest '{self.quest.id}': {json.dumps(self.dynamic_rewards, indent=2)}"

    def calculate_xp_reward(self, character: "Character", duration: int):
        """
        Calculates the experience points awarded based on quest duration.

        """
        base_xp = self.xp_rate
        time_xp = base_xp * duration

        # Temp disabling level scaling
        # character_level = character.level
        # level_scaling = 1 + (character_level * 0.05)
        level_scaling = 1

        # Temp disabling repeat penalty
        # quest_completions = character.get_quest_completions(self.quest).first()
        # times = quest_completions.times_completed if quest_completions else 0
        # midpoint = 50      # Adjust as needed
        # steepness = 0.1    # Adjust as needed
        # min_penalty = 0.8  # Lowest XP multiplier

        # exp_value = math.exp(-steepness * (times - midpoint))
        # repeat_penalty = min_penalty + (1 - min_penalty) / (1 + exp_value)
        repeat_penalty = 1

        final_xp = time_xp * level_scaling * repeat_penalty

        return max(1, round(final_xp))

    @transaction.atomic
    def apply(self, character: "Character"):
        """
        Apply the rewards associated with this quest to the given character, including
        coins, dynamic rewards, and buffs.

        """
        logger.info(
            f"[QUESTRESULTS.APPLY] Applying results for quest {self.quest.name} to character {character.name}"
        )
        # character.add_coins(self.coin_reward)
        character.coins += self.coin_reward

        if self.dynamic_rewards:
            rewards = cast(Dict[str, Any], self.dynamic_rewards or {})
            for key, value in rewards.items():
                if hasattr(character, f"apply_{key}"):
                    method = getattr(character, f"apply_{key}")
                    method(value)
                elif hasattr(character, key):
                    current_value = getattr(character, key)
                    if isinstance(current_value, (int, float)):
                        setattr(character, key, current_value + value)
                    else:
                        setattr(character, key, value)
        else:
            logger.info(
                f"[QUESTRESULTS.APPLY] No dynamic rewards found for quest {self.quest.name}."
            )

        # print("self.buffs:", self.buffs)
        for buff_name in self.buffs:
            # print("buff_name:", buff_name)
            buff = Buff.objects.get(name=buff_name)
            # print("questresults apply method, buff:", buff)
            applied_buff = AppliedBuff.objects.create(
                name=buff.name,
                duration=buff.duration,
                amount=buff.amount,
                buff_type=buff.buff_type,
                attribute=buff.attribute,
            )
            character.buffs.add(applied_buff)
        character.save()


class QuestRequirement(models.Model):
    """
    Represents the prerequisite quests a quest needs, including required completions.
    """

    quest = models.ForeignKey(
        Quest, on_delete=models.CASCADE, related_name="quest_requirements"
    )
    prerequisite = models.ForeignKey(
        Quest, on_delete=models.CASCADE, related_name="required_for"
    )
    times_required = models.PositiveIntegerField(default=1)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("quest", "prerequisite")

    def __str__(self):
        return f"{self.prerequisite.name} required {self.times_required} time(s) for {self.quest.name}"


class QuestCompletion(models.Model):
    """
    Tracks the completion details for a quest, including the number of times
    completed and the last completion timestamp.
    """

    character = models.ForeignKey(
        "character.Character", on_delete=models.CASCADE
    )  # don't add related_name, use character.quest_completions!
    quest = models.ForeignKey(
        "gameplay.Quest", on_delete=models.CASCADE, related_name="quest_completions"
    )
    times_completed = models.PositiveIntegerField(default=1)
    last_completed = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ("character", "quest")

    def __str__(self):
        return f"character {self.character.name} has completed {self.quest.name}"


class Skill(models.Model):
    profile = models.ForeignKey(
        "users.Profile", on_delete=models.CASCADE, related_name="skills"
    )
    name = models.CharField(max_length=100)
    time = models.PositiveIntegerField(default=0)
    xp = models.IntegerField(default=0)
    level = models.IntegerField(default=0)
    total_activities = models.PositiveIntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Project(models.Model):
    profile = models.ForeignKey(
        "users.Profile", on_delete=models.CASCADE, related_name="projects"
    )
    name = models.CharField(max_length=100)
    description = models.TextField(max_length=2000)
    time = models.PositiveIntegerField(default=0)
    total_activities = models.PositiveIntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Timer(models.Model):
    """
    An abstract base model that represents a general timer for activities
    such as quests or projects.
    """

    start_time = models.DateTimeField(null=True, blank=True)
    elapsed_time = models.IntegerField(default=0)  # Time in seconds
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

    @abstractmethod
    def calculate_xp(self) -> int:
        """Must be implemented by subclass to return XP."""
        raise NotImplementedError

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

    profile = models.OneToOneField(
        "users.profile", on_delete=models.CASCADE, related_name="activity_timer"
    )
    activity = models.ForeignKey(
        "progression.Activity",
        on_delete=models.SET_NULL,
        related_name="activity_timer",
        null=True,
        blank=True,
    )

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        logger.debug(f"[Activity timer save] Compute elapsed: {self.compute_elapsed()}")

    def __str__(self):
        return f"ActivityTimer {self.id} for {self.profile.name}"

    def new_activity(self, name=""):
        """
        Assign a new activity to the timer.

        """
        logger.debug(
            f"[ACTIVITYTIMER.new_activity]: Assigning new activity {name} to timer {self.pk}"
        )
        from progression.models import Activity

        self.activity = Activity.objects.create(name=name, profile=self.profile)

        if self.status == "empty":
            self.set_waiting()
        self.save(update_fields=["activity"])
        logger.debug(
            f"ActivityTimer after save: {self.pk}, activity: {self.activity}, status: {self.status}"
        )
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

    def complete(self):
        """
        Complete the activity timer and calculate the XP reward for the activity.

        """

        if not self.activity:
            logger.warning(
                f"[COMPLETE] Timer {self.id} has no activity assigned — skipping activity.complete()"
            )
            return 0

        if self.status == "completed":
            logger.warning(
                f"[COMPLETE CALLED AGAIN] Timer {self.id} already completed — elapsed_time: {self.elapsed_time}"
            )

        super().complete()
        self.update_activity_time()

        xp_gained = self.calculate_xp()
        self.profile.add_activity(self.elapsed_time, xp=xp_gained)

        message_text = f"Activity submitted. You got {xp_gained} XP!"
        ServerMessage.objects.create(
            group=self.profile.group_name,
            type="notification",
            action="notification",
            data={},
            message=message_text,
            is_draft=False,
        )

        self.activity.complete()
        logger.debug(
            f"[TIMER COMPLETE] Timer {self.id} completed — elapsed_time: {self.elapsed_time}, completed_at: {self.activity.completed_at}"
        )

        return self

    def _reset_hook(self):
        self.activity = None

    def reset(self):
        """
        Reset the activity timer and dissociate the current activity.
        """
        super().reset()
        self.activity = None
        self.save()

    def calculate_xp(self):
        """
        Calculate the XP reward for the associated activity.

        """
        if self.activity:
            return self.activity.calculate_xp_reward()
        return 0


class QuestTimer(Timer):
    """
    A timer that tracks progress on quests for a character.

    """

    character = models.OneToOneField(
        "character.Character", on_delete=models.CASCADE, related_name="quest_timer"
    )
    quest = models.ForeignKey(
        "progression.CharacterQuest",
        on_delete=models.SET_NULL,
        related_name="quest_timer",
        null=True,
        blank=True,
    )
    duration = models.IntegerField(default=0)

    def __str__(self):
        return f"QuestTimer {self.id} for {self.character.name}"

    def change_quest(self, quest, duration: int):
        """
        Reset the timer and change the associated quest.
        """
        from progression.utils import copy_quest

        self.reset()
        # self.quest = quest
        self.quest = copy_quest(self.character, quest)
        self.duration = duration
        self.set_waiting()
        self.save(update_fields=["quest", "duration", "status"])

    def complete(self):
        """
        Mark the quest timer as complete and calculate XP for the quest.
        """
        # logger.debug(f"[QUESTTIMER.COMPLETE] {self}")
        self.refresh_from_db()

        if not self.quest:
            logger.error("No quest found on timer %s", self.id)
            raise RuntimeError("Cannot complete: quest is None.")

        character = self.character
        if not self.character:
            logger.error("No character found on timer %s", self.id)
            raise RuntimeError("Cannot complete: character is None.")

        try:
            from character.models import PlayerCharacterLink

            profile = PlayerCharacterLink.get_profile(character)

            self.refresh_from_db()
            character.refresh_from_db()

            super().complete()

            xp_gained = self.calculate_xp()
            logger.debug(f"Quest timer, xp_gained: {xp_gained}")
            rewards_summary = character.complete_quest(xp_gained)

            completion_data = {
                "xp_gained": xp_gained,
                "rewards_summary": rewards_summary,
            }

            message_text = f"Quest completed. Character got {xp_gained} XP!"
            ServerMessage.objects.create(
                group=profile.group_name,
                type="notification",
                action="notification",
                data={"completion_data": completion_data},
                message=message_text,
                is_draft=False,
            )
            return self, character

        except Exception as e:
            import traceback

            logger.error(
                f"[CHAR.COMPLETE_QUEST] Error updating XP or quest count for character {self.id}: {e}"
            )
            logger.error(
                traceback.format_exc()
            )  # logs full stack trace of original error
            raise  # RuntimeError("Quest completion failed.") from e

    def reset(self):
        """
        Reset the quest timer and dissociate the quest.
        """
        super().reset()
        self.quest = None
        self.duration = 0
        self.save(
            update_fields=["quest", "status", "elapsed_time", "start_time", "duration"]
        )

    def _reset_hook(self):
        self.quest = None
        self.duration = 0

    def calculate_xp(self) -> int:
        """
        Calculate the XP reward for the associated quest.
        """

        if self.quest and hasattr(self.quest, "results"):
            return self.quest.results.calculate_xp_reward(self.character, self.duration)
        return 0

    def get_remaining_time(self):
        """
        Calculate the remaining time for the quest timer.
        """

        if self.status == "active":
            remaining = self.duration - self.get_elapsed_time()
        else:
            remaining = self.duration - self.elapsed_time
        return max(int(remaining), 0)

    def time_finished(self):
        """
        Check whether the quest timer is complete.

        :return: True if the timer has completed, False otherwise.
        :rtype: bool
        """
        # logger.debug(f"[QUESTTIMER.TIME FINISHED] Duration: {self.duration}, Remaining time: {self.get_remaining_time()}")
        return self.get_remaining_time() <= 0


class ServerMessage(models.Model):
    """
    Represents a message sent by the server to a specific user profile. This
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
        cutoff_date = timezone.now() - timezone.timedelta(days=days)
        cls.objects.filter(created_at__lt=cutoff_date).delete()


class Buff(models.Model):
    BUFF_TYPE_CHOICES = [
        ("additive", "Additive"),
        ("multiplicative", "Multiplicative"),
    ]

    name = models.CharField(max_length=100, default="Default buff name")
    attribute = models.CharField(max_length=50, default="Default buff attribute")
    duration = models.PositiveIntegerField(default=0)
    amount = models.FloatField(null=True, blank=True)
    buff_type = models.CharField(
        max_length=20, choices=BUFF_TYPE_CHOICES, default="additive"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)


class AppliedBuff(Buff):
    applied_at = models.DateTimeField(auto_now_add=True)
    ends_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.ends_at:
            self.ends_at = timezone.now() + timezone.timedelta(seconds=self.duration)
        super().save(*args, **kwargs)

    def is_active(self):
        """Check if buff is still active."""
        return timezone.now() < self.applied_at + timezone.timedelta(
            seconds=self.duration
        )

    def calc_value(self, total_value):
        if self.is_active():
            if self.buff_type == "additive":
                total_value += self.amount
            elif self.buff_type == "multiplicative":
                total_value *= self.amount
        return total_value
