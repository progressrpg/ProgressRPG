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


app.conf.beat_schedule = {
    # 'update-quests-every-hour': {
    #     'task': 'gameplay.tasks.update_quest_availability',
    #     'schedule': crontab(hour=0, minute=0), # Run every day
    # },
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
    "precompute-sun-times-daily": {
        "task": "gameworld.tasks.precompute_sun_times",
        "schedule": crontab(hour=0, minute=0),
        "args": (7,),  # keep 7 days ahead
    },
}
