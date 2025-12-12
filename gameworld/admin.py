from django.contrib import admin

from .models import DailySunTimes, GameWorld



@admin.register(DailySunTimes)
class DailySunTimesAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "date",
    ]
    list_filter = [
        "date",
    ]
    fields = [
        "id",
        "name",
        ("dawn", "dusk"),
        ("sunrise", "sunset"),
    ]

@admin.register(GameWorld)
class GameWorldAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "years_diff",
        "created_at",
    ]
    fields = [
        "name",
        ("latitude", "longitude"),
        "timezone",
        "years_diff",
        "created_at",
    ]
