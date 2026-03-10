from django.contrib import admin
from .models import Sheep,CalendarEvent

@admin.register(Sheep)
class SheepAdmin(admin.ModelAdmin):
    list_display = ('earing',)
    search_fields = ('earing',)


@admin.register(CalendarEvent)
class CalendarEventAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "start",
        "end",
        "group_id",
        "color",
    )

    list_filter = (
        "group_id",
        "start",
    )

    search_fields = (
        "title",
        "group_id",
    )

    ordering = ("-start",)

    fieldsets = (
        ("Event details", {
            "fields": (
                "title",
                ("start", "end"),
                "color",
            )
        }),
        ("Repeating / grouping", {
            "fields": (
                "group_id",
            ),
            "description": (
                "Use the same Group ID to link repeating events. "
                "You can delete or edit them together later."
            )
        }),
    )
