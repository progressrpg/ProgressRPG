from datetime import timedelta

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
    scheduled_task_ids = models.JSONField(default=list, blank=True)
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

        task_ids = []

        for minutes_until in times_to_schedule:
            message = f"Warning: maintenance is starting in {minutes_until} minute(s)!"
            result = send_warning.apply_async(
                kwargs={"message": message},
                eta=self.start_time - timedelta(minutes=minutes_until),
            )
            task_ids.append(result.id)
        logger.debug(
            f"[SCHEDULE TASKS] Scheduled {len(times_to_schedule)} maintenance warnings"
        )

        result = activate_maintenance.apply_async(
            kwargs={"window_id": self.id}, eta=self.start_time
        )
        task_ids.append(result.id)
        logger.debug(
            f"[SCHEDULE TASKS] Scheduled maintenance window to start at {self.start_time}"
        )

        self.tasks_scheduled = True
        self.scheduled_task_ids = task_ids
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
        self.tasks_scheduled = False
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

    def delete_scheduled_tasks(self):
        """Revokes scheduled Celery tasks for this maintenance window."""
        if not self.tasks_scheduled or not self.scheduled_task_ids:
            return False

        from celery import current_app

        for task_id in self.scheduled_task_ids:
            current_app.control.revoke(task_id)
            logger.debug(f"[DELETE TASKS] Revoked task {task_id}")

        logger.info(
            f"[DELETE TASKS] Revoked {len(self.scheduled_task_ids)} tasks for window '{self.name}'"
        )
        self.tasks_scheduled = False
        self.scheduled_task_ids = []
        self.save()
        return True
