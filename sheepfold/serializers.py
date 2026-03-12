from rest_framework import serializers
from .models import Milk, Sheep, BirthEvent, CalendarEvent


class MilkSerializer(serializers.ModelSerializer):
    # Accept earing on write, show earing on read
    sheep = serializers.SlugRelatedField(
        slug_field='earing',
        queryset=Sheep.objects.all(),
    )

    class Meta:
        model = Milk
        fields = ["id", "sheep", "date", "milk", "is_active"]


class SheepData(serializers.ModelSerializer):
    class Meta:
        model = Sheep
        fields = ["id", "earing", "birthdate", "gender", "mother", "is_active"]


class BirthEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = BirthEvent
        fields = ["id", "mother", "date", "notes", "lambs"]


class CalendarEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = CalendarEvent
        fields = ["id", "title", "start", "end", "group_id", "color"]
