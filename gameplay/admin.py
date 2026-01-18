from asgiref.sync import async_to_sync
from django.contrib import admin
from channels.layers import get_channel_layer
from .models import (
    Quest,
    QuestRequirement,
    QuestCompletion,
    ActivityTimer,
    QuestTimer,
    QuestResults,
    ServerMessage,
)


class QuestResultsInline(admin.TabularInline):
    model = QuestResults


@admin.register(Quest)
class QuestAdmin(admin.ModelAdmin):
    fields = [
        "name",
        "description",
        ("intro_text", "outro_text"),
        ("canRepeat", "is_premium", "is_task_support", "frequency"),
        ("levelMin", "levelMax"),
        "duration_choices",
        "created_at",
        ("stages", "stages_fixed"),
    ]
    list_display = [
        "name",
        # "is_premium",
        "created_at",
        "levelMin",
        "levelMax",
    ]
    list_filter = [
        "created_at",
        # "is_premium",
        # "frequency",
        "levelMin",
        "levelMax",
        "is_task_support",
    ]

    readonly_fields = [
        "created_at",
    ]
    inlines = [QuestResultsInline]


@admin.register(QuestResults)
class QuestResultsAdmin(admin.ModelAdmin):
    list_display = ["quest", "xp_rate", "coin_reward", "dynamic_rewards"]


@admin.register(QuestRequirement)
class QuestRequirementAdmin(admin.ModelAdmin):
    list_display = ["quest", "prerequisite", "times_required"]


@admin.register(QuestCompletion)
class QuestCompletionAdmin(admin.ModelAdmin):
    list_display = ["character", "quest", "times_completed"]
    fields = [
        "character",
        "quest",
        "times_completed",
        "last_completed",
    ]
    readonly_fields = ["last_completed"]


@admin.register(ActivityTimer)
class ActivityTimerAdmin(admin.ModelAdmin):
    list_display = ["profile", "activity", "elapsed_time", "status"]
    list_filter = [
        "status",
    ]
    actions = ["pause_timers", "reset_timers"]
    readonly_fields = ["profile"]

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "activity":
            # Get the profile from the object being edited
            obj = self.get_object(
                request, request.resolver_match.kwargs.get("object_id")
            )
            if obj and obj.profile:
                kwargs["queryset"] = db_field.remote_field.model.objects.filter(
                    profile=obj.profile
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


@admin.register(QuestTimer)
class QuestTimerAdmin(admin.ModelAdmin):
    list_display = ["character", "elapsed_time", "status"]
    list_filter = [
        "status",
    ]
    fields = [
        "character",
        "quest",
        "start_time",
        "elapsed_time",
        "duration",
        "status",
    ]
    actions = ["pause_timers", "reset_timers"]

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


# class CustomAdminSite(admin.AdminSite):
#     #change_list_template = "admin/combined_timers.html"
#     def get_urls(self):
#         urls = super().get_urls()
#         custom_urls = [
#             path('combined-timers/', self.admin_view(self.combined_timers_view), name='combined_timers'),
#         ]
#         return custom_urls + urls

#     def combined_timers_view(self, request):
#         activity_timers = ActivityTimer.objects.all()
#         quest_timers = QuestTimer.objects.all()
#         context = {
#             'title': 'Combined Timers',
#             'activity_timers': activity_timers,
#             'quest_timers': quest_timers,
#         }
#         return render(request, 'admin/combined_timers.html', context)

# custom_admin_site = CustomAdminSite(name='custom_admin')
# custom_admin_site.register(ActivityTimer)
# custom_admin_site.register(QuestTimer)
