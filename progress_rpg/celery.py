from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    os.getenv("DJANGO_SETTINGS_MODULE", "progress_rpg.settings.dev"),
)


app = Celery("progress_rpg")

app.config_from_object("django.conf:settings", namespace="CELERY")
app.conf.broker_connection_retry_on_startup = True

app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    print(f"Request: {self.request!r}")


CELERY_TIMEZONE = "Europe/London"

app.conf.beat_schedule = {
    # 'daily-character-death-check': {
    #     'task': 'gameworld.tasks.check_character_deaths',
    #     'schedule': crontab(hour=0, minute=0),
    # },
    # 'weekly-pregnancy-start': {
    #     'task': 'gameworld.tasks.start_character_pregnancies',
    #     'schedule': crontab(day_of_week=0, hour=0, minute=0),
    # },
    # 'weekly-pregnancy-check': {
    #     'task': 'gameworld.tasks.check_character_pregnancies',
    #     'schedule': crontab(day_of_week=0, hour=0, minute=0),
    # },
    "check_user_deletion": {
        "task": "users.tasks.perform_account_wipe",
        "schedule": crontab(minute=0, hour=0),
    },
    "reconcile_stale_online_players": {
        "task": "users.tasks.reconcile_stale_online_players",
        "schedule": 300.0,  # every 5 minutes
    },
    "auto_complete_timers_for_stale_players": {
        "task": "gameplay.tasks.auto_complete_timers_for_stale_players",
        "schedule": 30.0,  # every 30 seconds
    },
    "send_waitlist_nudges": {
        "task": "users.tasks.send_waitlist_nudges",
        "schedule": 7200.0,  # every 2 hours
    },
    "generate_character_days_1am": {
        "task": "character.tasks.generate_character_days",
        "schedule": crontab(hour=1, minute=0),
        "args": (),
    },
    "calculate-daily-metrics": {
        "task": "metrics.tasks.calculate_daily_metrics",
        "schedule": crontab(hour=1, minute=0),  # Daily at 1 AM
    },
    "calculate-weekly-metrics": {
        "task": "metrics.tasks.calculate_weekly_metrics",
        "schedule": crontab(hour=2, minute=0, day_of_week=1),  # Mondays at 2 AM
    },
    # "move_characters_tick": {
    #     "task": "locations.tasks.move_characters_tick",
    #     "schedule": 5.0,  # every 5 seconds
    # },
    "commute_tick": {
        "task": "locations.tasks.commute_tick",
        "schedule": 60.0,  # every 60 seconds
    },
    "advance_field_economy": {
        "task": "economy.tasks.advance_field_economy_tick",
        "schedule": crontab(hour=18, minute=5),  # 5 min after WORK_END
    },
    "advance_mill_economy": {
        "task": "economy.tasks.advance_mill_economy_tick",
        "schedule": crontab(hour=18, minute=10),  # after advance_field_economy
    },
    "advance_bakery_economy": {
        "task": "economy.tasks.advance_bakery_economy_tick",
        "schedule": crontab(hour=18, minute=15),  # after advance_mill_economy
    },
    "advance_bread_consumption": {
        "task": "economy.tasks.advance_bread_consumption_tick",
        "schedule": crontab(hour=18, minute=20),  # after advance_bakery_economy
    },
    # "precompute-sun-times-daily": {
    #     "task": "gameworld.tasks.precompute_sun_times",
    #     "schedule": crontab(hour=0, minute=0),
    #     "args": (7,),  # keep 7 days ahead
    # },
}
