from django.contrib import admin
from .models import Sheep, BirthEvent, Milk, CalendarEvent, FarmMilkSettings


@admin.register(FarmMilkSettings)
class FarmMilkSettingsAdmin(admin.ModelAdmin):
    list_display = ('farm', 'period_days', 'high_threshold', 'med_threshold', 'low_threshold')
    list_select_related = ('farm',)


@admin.register(Sheep)
class SheepAdmin(admin.ModelAdmin):
    list_display = ('earing', 'farm', 'gender', 'group', 'ready_for_birth', 'birthdate', 'is_active')
    list_filter = ('farm', 'gender', 'group', 'is_active')
    search_fields = ('earing',)


@admin.register(BirthEvent)
class BirthEventAdmin(admin.ModelAdmin):
    list_display = ('mother', 'date')
    list_filter = ('date',)


@admin.register(Milk)
class MilkAdmin(admin.ModelAdmin):
    list_display = ('sheep', 'date', 'milk', 'is_active')
    list_filter = ('is_active', 'date', 'sheep__farm')


@admin.register(CalendarEvent)
class CalendarEventAdmin(admin.ModelAdmin):
    list_display = ("title", "farm", "start", "end", "group_id", "color")
    list_filter = ("farm", "group_id", "start")
    search_fields = ("title", "group_id")
    ordering = ("-start",)

    fieldsets = (
        ("Event details", {
            "fields": ("farm", "title", ("start", "end"), "color")
        }),
        ("Repeating / grouping", {
            "fields": ("group_id",),
            "description": (
                "Use the same Group ID to link repeating events. "
                "You can delete or edit them together later."
            )
        }),
    )
