from celery import shared_task
from django.utils import timezone
import subprocess
from gameplay.models import ServerMessage
from server_management.models import MaintenanceWindow
import logging

logger = logging.getLogger("general")


@shared_task
def send_warning(message="Warning: maintenance is approaching!"):
    print("⚠️ Warning: Scheduled maintenance is approaching!")
    # Add toast notification logic here
    ServerMessage.objects.create(
        group="online_users",
        type="notification",
        action="notification",
        data={},
        message=message,
        is_draft=False,
    )


@shared_task
def activate_maintenance(window_id):
    """Activates the maintenance window when scheduled."""
    logger.info(f"[TASK ACTIVATE MAINTENANCE]")

    message = (
        "Maintenance is starting! Your timers will be paused and your progress saved."
    )

    ServerMessage.objects.create(
        group="online_users",
        type="notification",
        action="notification",
        data={},
        message=message,
        is_draft=False,
    )

    window = MaintenanceWindow.objects.get(id=window_id)

    if not window.is_active:
        window.activate_maintenance()


@shared_task
def deactivate_maintenance():
    subprocess.run(["python", "server_management/scripts/deactivate_maintenance.py"])
