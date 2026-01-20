# gameworld.models

from django.db import models
from django.utils import timezone
from django.utils.timezone import timedelta, now
from datetime import datetime, date
import random, math
import numpy as np

from progression.models import PlayerActivity
from users.models import Player


# Don't think I actually need this after all!
# I can use created_at fields which have time too
class DailyStats(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)  # auto_now_add=True
    newUsers = models.PositiveIntegerField(default=0)
    questsCompleted = models.PositiveIntegerField(default=0)
    activitiesCompleted = models.PositiveIntegerField(default=0)
    activityTimeLogged = models.PositiveIntegerField(default=0)
    today = now().date()
    recordDate = models.DateField(default=now)

    def __str__(self):
        return f"Daily Stats for {self.recordDate} \
            {self.newUsers} new users, "


class GameWorld(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    name = models.CharField(max_length=100)
    num_profiles = models.PositiveIntegerField(default=0)
    highest_login_streak_ever = models.PositiveIntegerField(default=0)
    highest_login_streak_current = models.PositiveIntegerField(default=0)
    total_activity_num = models.PositiveIntegerField(default=0)
    total_activity_time = models.PositiveIntegerField(default=0)
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

    def update(self):
        players = Player.objects.all()
        self.num_profiles = len(profiles)
        for player in players:
            if self.highest_login_streak_ever < player.login_streak_max:
                self.highest_login_streak_ever = player.login_streak_max
            if self.highest_login_streak_current < player.login_streak:
                self.highest_login_streak_current = player.login_streak

        activities = PlayerActivity.objects.all()
        self.total_activity_num = len(activities)
        total_activity_time = 0
        for activity in activities:
            total_activity_time += activity.duration
        self.total_activity_time = total_activity_time

        activities_num_average = self.total_activity_num / self.num_profiles
        activities_time_average = self.total_activity_time / self.num_profiles

    def createDailyStats(self):
        ds = DailyStats.objects.create(
            name=f"DailyStats for world {self.name}",
        )

    def __str__(self):
        return f"GameWorld {self.name}"

    def display(self):
        return (
            f"This game has been running for {self.time_up()} since {self.created_at}"
        )


class Season(models.Model):
    SEASON_CHOICES = [
        ("Spring", "Spring"),
        ("Summer", "Summer"),
        ("Autumn", "Autumn"),
        ("Winter", "Winter"),
    ]

    name = models.CharField(max_length=6, choices=SEASON_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField()
    year = models.IntegerField()

    def __str__(self):
        return f"{self.season_name} {self.year}"

    def game_year(self, game_calendar):
        """Get the game year for this season."""
        return game_calendar.real_to_game_date(self.start_date)[0]

    @classmethod
    def get_seasonal_temperature_range(cls, season_name):
        SEASONAL_TEMPERATURE_RANGES = {
            "Spring": (10, 20),
            "Summer": (15, 30),
            "Autumn": (5, 15),
            "Winter": (-5, 5),
        }
        return SEASONAL_TEMPERATURE_RANGES[season_name]


class WeatherType(models.Model):
    name = models.CharField(max_length=50)
    description = models.TextField(blank=True, null=True)
    min_temp_change = models.IntegerField()
    max_temp_change = models.IntegerField()
    typical_duration = models.IntegerField(default=3)  # default duration in days
    crop_growth_modifier = models.FloatField(default=1.0)
    travel_speed_modifier = models.FloatField(default=1.0)
    cleanliness_modifier = models.FloatField(default=1.0)

    def __str__(self):
        return self.name


class WeatherEvent(models.Model):
    start = models.DateTimeField(null=True)
    end = models.DateTimeField(null=True)
    weather_type = models.ForeignKey(
        "WeatherType", on_delete=models.SET_NULL, null=True
    )
    base_temperature = models.IntegerField()
    location = models.ForeignKey(
        "locations.Location", on_delete=models.CASCADE, null=True, blank=True
    )
    season = models.ForeignKey(
        "Season", on_delete=models.CASCADE, null=True, blank=True
    )

    def generate_hourly_temperatures(self, start_temperature=None):
        num_hours = int((self.end - self.start).total_seconds() // 3600)
        temperatures = []

        season_name = self.season.name
        min_temp, max_temp = self.season.get_seasonal_temperature_range(season_name)
        temperature_gradient = np.linspace(min_temp, max_temp, num_hours)

        for hour in range(num_hours):
            # Calculate hour of day (0-23)
            hour_of_day = (self.start + timedelta(hours=hour)).hour

            # Define a daily temp profile (sine wave)
            if start_temperature is not None and hour == 0:
                daily_temp_profile = start_temperature
            else:
                daily_temp_profile = temperature_gradient[hour] + 5 * math.sin(
                    (hour_of_day - 6) * math.pi / 12
                )

            # Apply random variations
            random_variation = random.uniform(-1, 1)
            temperature = daily_temp_profile + random_variation
            temperatures.append(temperature)

        return temperatures

    def __str__(self):
        return f"{self.weather_type.name} ({self.start} - {self.end})"

    def display(self):
        return f"WeatherEvent. Starts {self.start}, ends {self.end}. Type: {self.weather_type.name}. Base temp: {self.base_temperature}"


class Weather(models.Model):
    date = models.DateTimeField()
    season = models.ForeignKey(
        "Season", on_delete=models.CASCADE, null=True, blank=True
    )
    weather_event = models.ForeignKey(
        "WeatherEvent", on_delete=models.CASCADE, null=True, blank=True
    )
    temperature = models.IntegerField()
    crop_growth_modifier = models.FloatField(default=1.0)
    travel_speed_modifier = models.FloatField(default=1.0)
    cleanliness_modifier = models.FloatField(default=1.0)

    @classmethod
    def get_season_for_date(cls, date):
        month = date.month
        if month in [3, 4, 5]:
            return Season.objects.get(name="Spring")
        elif month in [6, 7, 8]:
            return Season.objects.get(name="Summer")
        elif month in [9, 10, 11]:
            return Season.objects.get(name="Autumn")
        elif month in [12, 1, 2]:
            return Season.objects.get(name="Winter")

    @classmethod
    def generate_weather_forecast(cls, game_world, start_date=None, days_ahead=30):
        if not start_date:
            start_date = game_world.convert_to_game_date(now())

        end_date = start_date + timedelta(days=days_ahead)
        current_date = start_date
        last_temperature = None

        while current_date < end_date:
            # Check if there's already a weather event covering this day
            current_game_date = current_date
            for s in Season.objects.all():
                print(f"{s.name}, {s.start_date.year}")
            print(f"Current game date: {current_game_date.date()}")
            current_season = Season.objects.filter(
                start_date__lte=current_game_date.date()
            ).first()
            print(f"Current season: {current_season.name}")
            existing_event = WeatherEvent.objects.filter(
                start__lte=current_game_date.date(), end__gte=current_game_date.date()
            ).first()

            if not existing_event:
                min_temp, max_temp = current_season.get_seasonal_temperature_range(
                    current_season.name
                )
                base_temp = random.randint(min_temp, max_temp)
                weather_type = random.choice(WeatherType.objects.all())
                duration = random.randint(2, weather_type.typical_duration + 2)
                end_event_date = current_game_date + timedelta(days=duration - 1)
                # Seems to be getting timezone naive dates, but they shouldn't be...
                event = WeatherEvent.objects.create(
                    start=current_game_date,
                    end=end_event_date,
                    weather_type=weather_type,
                    base_temperature=base_temp,
                    season=current_season,
                )

            else:
                event = existing_event

            print("Event testing:", event)
            hourly_temperatures = event.generate_hourly_temperatures(
                start_temperature=last_temperature
            )

            for hour_offset in range(len(hourly_temperatures)):
                hour_timestamp = event.start + timedelta(hours=hour_offset)

                if hour_timestamp >= end_date:
                    break

                last_temperature = hourly_temperatures[hour_offset]
                Weather.objects.create(
                    date=hour_timestamp,
                    season=cls.get_season_for_date(hour_timestamp),
                    weather_event=event,
                    temperature=last_temperature,
                )

            current_date = event.end + timedelta(days=1)  # Move past this event
        # End of while loop

    @classmethod
    def get_forecast(cls, gw, days_ahead=7):
        """Retrieve the weather forecast for the next X days"""
        today = now()
        game_today = gw.convert_to_game_date(today)
        return cls.objects.filter(
            date__gte=game_today, date__lte=game_today + timedelta(days=days_ahead)
        )

    @classmethod
    def get_season_for_dote(cls, date):
        month = date.month
        if month in [3, 4, 5]:
            return "Spring"
        elif month in [6, 7, 8]:
            return "Summer"
        elif month in [9, 10, 11]:
            return "Autumn"
        elif month in [12, 1, 2]:
            return "Winter"

    def get_temperature(self):
        min_temp, max_temp = self.BASE_TEMPERATURES[self.season]
        temperature_change = random.randint(
            self.weather_type.min_temp_change, self.weather_type.max_temp_change
        )
        new_temp = random.randint(min_temp, max_temp) + temperature_change
        return new_temp

    @classmethod
    def get_hourly_temperatures(cls, date):
        # Ensure the date is a datetime object and set the start and end time for the day
        start_of_day = timezone.make_aware(datetime.combine(date, datetime.min.time()))
        end_of_day = start_of_day + timedelta(days=1)

        print(f"Start of day: {start_of_day}, End of day: {end_of_day}")

        # Query the Weather model for temperatures within the specified date range
        weather_entries = cls.objects.filter(
            date__gte=start_of_day, date__lt=end_of_day
        ).order_by("date")

        # for w in weather_entries:
        #    print(w.display())

        # Extract the temperatures into a list
        temperatures = [entry.temperature for entry in weather_entries]

        return temperatures

    @classmethod
    def get_high_and_low(cls, date):
        temperatures = cls.get_hourly_temperatures(date)
        high_temperature = max(temperatures) if temperatures else None
        low_temperature = min(temperatures) if temperatures else None
        high_low = [high_temperature, low_temperature]
        return high_low

    def update_weather(self):
        self.season = self.get_season()
        self.temperature = self.get_temperature()
        self.crop_growth_modifier = self.weather_type.crop_growth_modifier
        self.travel_speed_modifier = self.weather_type.travel_speed_modifier
        self.cleanliness_modifier = self.weather_type.cleanliness_modifier
        self.save()

    def save(self, *args, **kwargs):
        self.season = self.get_season_for_date(self.date.date())
        super().save(*args, **kwargs)

    def display(self):
        return (
            f"Weather. Date: {self.date}, season {self.season}, temp {self.temperature}"
        )
