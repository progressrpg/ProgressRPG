import django
import os, subprocess
from django.utils import timezone


os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    os.getenv("DJANGO_SETTINGS_MODULE", "progress_rpg.settings.dev"),
)
django.setup()

import logging

logger = logging.getLogger("general")


def restart_services():
    """Restart essential services to ensure system stability."""
    logger.info("Restarting services...")
    # subprocess.run(["sudo", "systemctl", "restart", "celery.service"])
    subprocess.run(["pkill", "-f", "celery"])  # ✅ Kill any running Celery workers
    subprocess.Popen(
        ["celery", "-A", "progress_rpg", "worker", "--loglevel=debug"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )  # ✅ Restart the worker
    # subprocess.run(["sudo", "systemctl", "restart", "daphne"])
    subprocess.run(["sudo", "systemctl", "restart", "redis-server.service"])
    logger.info("All services restarted.")


def check_logs():
    """Check logs for errors after maintenance."""
    logger.info("Checking logs for issues...")
    subprocess.run(
        "journalctl -u progress_rpg --no-pager | tail -n 50", shell=True, check=True
    )


def verify_status():
    """Verify key status pages."""
    logger.info("Checking status pages...PLACEHOLDER! ADMINS NO STATUS!")
    # response = subprocess.run(["curl", "-I", "http://localhost/status"], capture_output=True, text=True)
    # logger.info(response.stdout)


def notify_admins():
    """Send an alert if recovery detected any issues."""
    logger.info("Notifying admins...PLACEHOLDER! ADMINS KNOW NOTHING!")
    # from server_management.utils import send_admin_alert
    # send_admin_alert("🚨 Post-maintenance recovery executed. Check logs for potential issues.")


def deactivate_maintenance():
    from server_management.models import MaintenanceWindow

    active_windows = MaintenanceWindow.objects.filter(is_active=True)
    for window in active_windows:
        window.deactivate_maintenance()


def run():
    # restart_services()
    check_logs()
    verify_status()
    notify_admins()
    deactivate_maintenance()
