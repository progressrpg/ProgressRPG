from django.db import models
from django.utils.timezone import now, timedelta
from datetime import datetime
from users.models import Player
import json
import math


class Event(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("active", "Active"),
        ("completed", "Completed"),
    ]

    name = models.CharField(max_length=255)
    description = models.TextField()
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    goal_seconds = models.PositiveIntegerField()  # Total time goal in seconds
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)

    def all_goals_completed(self):
        return self.eventgoals.all().filter(completed=False).count() == 0

    def check_completed(self):
        if self.all_goals_completed():
            self.complete()

    def complete(self):
        pass

    def __str__(self):
        return f"Event: {self.name} - {self.status}"


class EventGoal(models.Model):
    GOAL_TYPES = [
        ("time", "Time"),
    ]
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("active", "Active"),
        ("completed", "Completed"),
    ]

    event = models.ForeignKey(Event, related_name="goal", on_delete=models.CASCADE)
    goal_type = models.CharField(max_length=50, choices=GOAL_TYPES)
    goal_value = models.IntegerField()
    progress_value = models.IntegerField(default=0)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")

    def is_completed(self):
        """Checks if goal has been completed"""
        return self.current_value >= self.goal_value

    def update_progress(self, value):
        """Updates the current progress"""
        self.progress_value += value

        if self.is_completed():
            self.status = "completed"
            self.event.check_completed()
        self.save()

    def __str__(self):
        return f"Goal for {self.event.name}: {self.goal_type} {self.current_value}/{self.goal_value}"


class EventContribution(models.Model):
    player = models.ForeignKey(
        Player, related_name="contribution", on_delete=models.CASCADE
    )
    event_goal = models.ForeignKey(
        EventGoal, related_name="contribution", on_delete=models.CASCADE
    )
    progress_value = models.IntegerField(default=0)  # User-specific progress
    last_updated = models.DateTimeField(auto_now=True)

    def update_progress(self, value):
        if not self.event_goal.is_completed():
            self.progress_value += value
            self.save()
            self.event_goal.update_progress(value)
