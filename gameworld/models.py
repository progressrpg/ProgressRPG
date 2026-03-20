# gameworld.models

from django.db import models
from django.utils.timezone import now
from datetime import datetime, date
from astral import LocationInfo
from astral.sun import sun
import random, math
import numpy as np

from users.models import Player
from gameplay.models import QuestCompletion


class DailySunTimes(models.Model):
    world = models.ForeignKey(
        "GameWorld", on_delete=models.CASCADE, related_name="sun_times"
    )
    date = models.DateField(unique=True)
    sunrise = models.DateTimeField()
    sunset = models.DateTimeField()
    dawn = models.DateTimeField()
    dusk = models.DateTimeField()

    class Meta:
        unique_together = ("world", "date")
        ordering = ["date"]


class GameWorld(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    name = models.CharField(max_length=100)
    latitude = models.FloatField(default=51.5074)
    longitude = models.FloatField(default=-0.1278)
    timezone = models.CharField(max_length=50, default="Europe/London")

    years_diff = models.IntegerField(blank=True, null=True)

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get_instance(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def current_sun_phase(self, now=None):
        """
        Returns one of 'night', 'dawn', 'day', or 'dusk'
        based on precomputed sun times for today.
        """
        from .models import DailySunTimes

        if now is None:
            now = datetime.now().astimezone()

        today_times = self.sun_times.get(date=now.date())

        if now < today_times.dawn:
            return "night"
        elif now < today_times.sunrise:
            return "dawn"
        elif now < today_times.sunset:
            return "day"
        elif now < today_times.dusk:
            return "dusk"
        else:
            return "night"

    def convert_to_game_date(self, input_date):
        """Convert a date or datetime object to a chosen distance in the past."""
        if isinstance(input_date, datetime):
            new_year = input_date.year + self.years_diff
            new_date = input_date.replace(year=new_year)
            print(f"New date: {new_date}, {type(new_date)}")
            return new_date
        elif isinstance(input_date, date):
            new_year = input_date.year + self.years_diff
            return input_date.replace(year=new_year)
        else:
            raise TypeError("Input must be a date or datetime object")

    def convert_to_original_date(self, modified_date):
        """Convert a modified date or datetime object back to its original year."""
        original_year = modified_date.year - self.years_diff
        if isinstance(modified_date, datetime):
            return modified_date.replace(year=original_year)
        elif isinstance(modified_date, date):
            return modified_date.replace(year=original_year)
        else:
            raise TypeError("Input must be a date or datetime object")

    def time_up(self):
        return now() - self.created_at

    def __str__(self):
        return f"GameWorld {self.name}"

    def display(self):
        return (
            f"This game has been running for {self.time_up()} since {self.created_at}"
        )
