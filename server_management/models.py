from django.db import models
from django.utils import timezone
import subprocess
from celery import Celery
from django.shortcuts import redirect
import logging
from asgiref.sync import async_to_sync
from gameplay.utils import send_group_message

logger = logging.getLogger("general")


class MaintenanceWindow(models.Model):
    name = models.CharField(max_length=100)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    description = models.TextField(blank=True)
    tasks_scheduled = models.BooleanField(default=False)
    is_active = models.BooleanField(default=False)

    def __str__(self):
        return self.name

    def mark_tasks_scheduled(self):
        self.tasks_scheduled = True
        self.save()

    def schedule_tasks(self):
        """Schedules Celery tasks if not already scheduled."""
        logger.info("[SCHEDULE TASKS] Scheduling maintenance window tasks")
        now = timezone.now()
        if self.tasks_scheduled:
            return False
        if self.end_time < now:
            return False

        from server_management.tasks import send_warning, activate_maintenance

        # List of warning times in minutes
        warning_times = [30, 15, 10, 5, 3, 2, 1]

        minutes_to_start = (self.start_time - now).total_seconds() / 60

        times_to_schedule = [t for t in warning_times if t <= minutes_to_start]

        for minutes_until in times_to_schedule:
            message = f"Warning: maintenance is starting in {minutes_until} minute(s)!"
            send_warning.apply_async(
                kwargs={"message": message},
                eta=self.start_time - timezone.timedelta(minutes=minutes_until),
            )
        logger.debug(
            f"[SCHEDULE TASKS] Scheduled {len(times_to_schedule)} maintenance warnings"
        )

        activate_maintenance.apply_async(
            kwargs={"window_id": self.id}, eta=self.start_time
        )
        logger.debug(
            f"[SCHEDULE TASKS] Scheduled maintenance window to start at {self.start_time}"
        )

        self.tasks_scheduled = True
        self.save()
        return True

    def activate_maintenance(self):
        logger.info("[ACTIVATE MAINTENANCE] Activating maintenance mode...")
        now = timezone.now()
        subprocess.run(["python", "manage.py", "pause_timers"])
        payload = {
            "type": "action",
            "action": "refresh",
            "data": {
                "maintenance_active": True,
                "name": self.name,
                "description": self.description,
                "start_time": self.start_time.isoformat(),
                "end_time": self.end_time.isoformat(),
            },
            "success": True,
        }

        async_to_sync(send_group_message)("online_users", payload)

        self.is_active = True
        self.save()
        # Add any additional activation logic here.

    def deactivate_maintenance(self):
        logger.info("[DEACTIVATE MAINTENANCE] Deactivating maintenance mode...")
        print("Deactivating maintenance mode... wrapping up!")
        self.is_active = False
        self.save()

        payload = {
            "type": "action",
            "action": "refresh",
            "data": {
                "maintenance_active": False,
            },
            "success": True,
        }

        async_to_sync(send_group_message)("online_users", payload)

    # def delete_scheduled_tasks(self):
    #     """Deletes scheduled tasks if necessary."""
    #     from celery.task.control import revoke
    #     # Logic to track and revoke tasks (requires storing task IDs)
    #     self.tasks_scheduled = False
    #     self.save()


class FeatureFlag(models.Model):
    class AccessLevel(models.TextChoices):
        NO = "no", "No users"
        ALL = "all", "All users"
        PREMIUM = "premium", "Premium users"

    key = models.CharField(max_length=100, unique=True)
    access_level = models.CharField(
        max_length=16,
        choices=AccessLevel.choices,
        default=AccessLevel.NO,
    )
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("key",)

    def __str__(self):
        return f"{self.key} ({self.access_level})"

    @classmethod
    def as_dict(cls):
        return dict(cls.objects.values_list("key", "access_level"))
