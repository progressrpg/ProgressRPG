from django.contrib import admin
from django.utils.timezone import now
from .models import FeatureFlag, MaintenanceWindow
import re
import subprocess
from pathlib import Path
from django import forms
from django.conf import settings
from django.shortcuts import redirect
from django.http import HttpResponseRedirect
from django.urls import path
from asgiref.sync import async_to_sync
import logging
from gameplay.utils import send_group_message
from django.utils.html import format_html

_FEATURE_FLAGS_TS = settings.BASE_DIR / "frontend" / "src" / "featureFlags.ts"
_FLAG_KEY_RE = re.compile(r"^\s{2}(\w+):\s*\[", re.MULTILINE)

_ACCESS_GROUP_CHOICES = [
    ("all", "All users"),
    ("premium", "Premium users"),
    ("testers", "Testers"),
]


def _load_flag_key_choices(exclude=()):
    try:
        text = _FEATURE_FLAGS_TS.read_text()
        keys = _FLAG_KEY_RE.findall(text)
    except FileNotFoundError:
        return []
    return [(k, k) for k in keys if k not in exclude]


class FeatureFlagForm(forms.ModelForm):
    access_groups = forms.MultipleChoiceField(
        choices=_ACCESS_GROUP_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=False,
    )

    class Meta:
        model = FeatureFlag
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Exclude keys already assigned to another FeatureFlag row, so the
        # dropdown only offers keys that don't have one yet. When editing an
        # existing row, its own key stays selectable.
        already_used = set(
            FeatureFlag.objects.exclude(pk=self.instance.pk).values_list(
                "key", flat=True
            )
        )
        self.fields["key"] = forms.ChoiceField(
            choices=_load_flag_key_choices(exclude=already_used)
        )


logger = logging.getLogger("general")


@admin.register(MaintenanceWindow)
class MaintenanceWindowAdmin(admin.ModelAdmin):
    list_display = ("name", "start_time", "end_time", "is_active", "tasks_scheduled")
    ordering = ("start_time",)
    search_fields = ("name", "description")
    readonly_fields = [
        "is_active",
    ]

    # actions = [schedule_window_tasks, delete_window_tasks] #, activate_maintenance, deactivate_maintenance

    def schedule_tasks(self, request, maintenancewindow_id):
        logger.info(f"[ADMIN - SCHEDULE TASKS]")
        window = self.get_object(request, maintenancewindow_id)
        if window is None:
            self.message_user(request, "Maintenance window not found.")
            return redirect("/admin/server_management/maintenancewindow/")

        success = window.schedule_tasks()

        if success:
            self.message_user(request, f"Tasks scheduled for window '{window.name}'.")
        else:
            self.message_user(request, f"Tasks already scheduled: no action taken.")
        return redirect(
            f"/admin/server_management/maintenancewindow/{maintenancewindow_id}/change/"
        )

    def delete_tasks(self, request, maintenancewindow_id):
        logger.info(f"[ADMIN - DELETE TASKS]")
        window = self.get_object(request, maintenancewindow_id)
        if window is None:
            self.message_user(request, "Maintenance window not found.")
            return redirect("/admin/server_management/maintenancewindow/")

        success = window.delete_scheduled_tasks()

        if success:
            self.message_user(
                request, f"Scheduled tasks deleted for window '{window.name}'."
            )
        else:
            self.message_user(
                request, f"No scheduled tasks to delete: no action taken."
            )
        return redirect(
            f"/admin/server_management/maintenancewindow/{maintenancewindow_id}/change/"
        )

    def activate_maintenance(self, request, maintenancewindow_id):
        window = self.get_object(request, maintenancewindow_id)
        if window is None:
            self.message_user(request, "Maintenance window not found.")
            return redirect("/admin/server_management/maintenancewindow/")
        if not window.is_active:
            window.activate_maintenance()
            player = request.user.player
            async_to_sync(send_group_message)(
                "online_users", {"type": "action", "action": "refresh", "success": True}
            )
            self.message_user(
                request, f"Maintenance window '{window.name}' now active!"
            )
        else:
            self.message_user(
                request, f"Maintenance window is already active: no action taken."
            )
        return redirect(
            f"/admin/server_management/maintenancewindow/{maintenancewindow_id}/change/"
        )

    def deactivate_maintenance(self, request, maintenancewindow_id):
        window = self.get_object(request, maintenancewindow_id)
        if window is None:
            self.message_user(request, "Maintenance window not found.")
            return redirect("/admin/server_management/maintenancewindow/")
        if window.is_active:
            window.deactivate_maintenance()
            player = request.user.player
            async_to_sync(send_group_message)(
                "online_users",
                {"type": "action", "action": "load-game", "success": True},
            )
            self.message_user(
                request,
                f"Maintenance window '{window.name}' deactivated.",
            )
        else:
            self.message_user(
                request, f"Maintenance window is not activated: no action taken."
            )
        return redirect(
            f"/admin/server_management/maintenancewindow/{maintenancewindow_id}/change/"
        )

    # Define custom admin URL
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "<int:maintenancewindow_id>/delete-tasks/",
                self.admin_site.admin_view(self.delete_tasks),
                name="delete_tasks",
            ),
            path(
                "<int:maintenancewindow_id>/schedule/",
                self.admin_site.admin_view(self.schedule_tasks),
                name="schedule_tasks",
            ),
            path(
                "<int:maintenancewindow_id>/activate/",
                self.admin_site.admin_view(self.activate_maintenance),
                name="activate_maintenance",
            ),
            path(
                "<int:maintenancewindow_id>/deactivate/",
                self.admin_site.admin_view(self.deactivate_maintenance),
                name="deactivate_maintenance",
            ),
        ]
        return custom_urls + urls

    def change_view(self, request, object_id, form_url="", extra_context=None):
        extra_context = extra_context or {}
        extra_context["delete_url"] = (
            f"/admin/server_management/maintenancewindow/{object_id}/delete-tasks/"
        )
        extra_context["schedule_url"] = (
            f"/admin/server_management/maintenancewindow/{object_id}/schedule/"
        )
        extra_context["activate_url"] = (
            f"/admin/server_management/maintenancewindow/{object_id}/activate/"
        )
        extra_context["deactivate_url"] = (
            f"/admin/server_management/maintenancewindow/{object_id}/deactivate/"  # Add this line
        )
        return super().change_view(request, object_id, form_url, extra_context)


@admin.register(FeatureFlag)
class FeatureFlagAdmin(admin.ModelAdmin):
    form = FeatureFlagForm
    list_display = ("key", "get_access_groups_display", "updated_at")
    search_fields = ("key", "description")

    @admin.display(description="Access groups")
    def get_access_groups_display(self, obj):
        return ", ".join(obj.access_groups) if obj.access_groups else "—"
