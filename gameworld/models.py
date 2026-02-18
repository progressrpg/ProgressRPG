# gameworld.models

from django.db import models
from django.utils.timezone import now
from datetime import datetime, date


class GameWorld(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    name = models.CharField(max_length=100)
    years_diff = models.IntegerField()

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
