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
    "move_characters_tick": {
        "task": "character.tasks.move_characters_tick",
        "schedule": 5.0,  # every 5 seconds
    },
    "precompute-sun-times-daily": {
        "task": "gameworld.tasks.precompute_sun_times",
        "schedule": crontab(hour=0, minute=0),
        "args": (7,),  # keep 7 days ahead
    },
}
