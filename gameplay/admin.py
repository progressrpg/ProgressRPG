from asgiref.sync import async_to_sync
from django.contrib import admin
from channels.layers import get_channel_layer
from .models import (
    ActivityTimer,
    ServerMessage,
    XpModifier,
)


@admin.register(ActivityTimer)
class ActivityTimerAdmin(admin.ModelAdmin):
    list_display = ["player", "activity", "elapsed_time", "status"]
    list_filter = [
        "status",
    ]
    actions = ["pause_timers", "reset_timers"]
    readonly_fields = ["player"]

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "activity":
            # Get the player from the object being edited
            obj = self.get_object(
                request, request.resolver_match.kwargs.get("object_id")
            )
            if obj and obj.player:
                kwargs["queryset"] = db_field.remote_field.model.objects.filter(
                    player=obj.player
                )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    @admin.display(description="Pause selected timers")
    def pause_timers(self, request, queryset):
        for timer in queryset:
            timer.pause()
        self.message_user(request, "Selected timers have been paused.")

    @admin.display(description="Reset selected timers")
    def reset_timers(self, request, queryset):
        for timer in queryset:
            timer.reset()
        self.message_user(request, "Selected timers have been reset.")


@admin.action(description="Send selected ServerMessages")
def send_selected_messages(modeladmin, request, queryset):
    """Manually sends non-draft ServerMessages via WebSockets."""
    channel_layer = get_channel_layer()

    groups_to_notify = (
        queryset.filter(is_draft=False).values_list("group", flat=True).distinct()
    )
    if not groups_to_notify:
        modeladmin.message_user(
            request, "No groups found for sending pending messages."
        )
        return

    for group in groups_to_notify:
        async_to_sync(channel_layer.group_send)(
            group, {"type": "send_pending_messages"}
        )


@admin.register(ServerMessage)
class ServerMessageAdmin(admin.ModelAdmin):
    list_display = [
        "group",
        "message",
        "created_at",
        "is_draft",
        "is_delivered",
    ]
    list_filter = [
        "group",
        "created_at",
        "is_delivered",
    ]
    fields = [
        "group",
        "type",
        "action",
        "message",
        "data",
        "is_draft",
        "is_delivered",
        "created_at",
    ]
    readonly_fields = ["created_at"]
    actions = [send_selected_messages]


@admin.register(XpModifier)
class XpModifierAdmin(admin.ModelAdmin):
    list_display = [
        "key",
        "scope",
        "player",
        "character",
        "multiplier",
        "starts_at",
        "ends_at",
        "is_active",
        "created_at",
        "last_updated",
    ]
    list_filter = [
        "scope",
        "is_active",
        "starts_at",
        "ends_at",
        "created_at",
    ]
    search_fields = [
        "key",
        "player__name",
        "character__name",
    ]
    readonly_fields = [
        "created_at",
        "last_updated",
    ]
