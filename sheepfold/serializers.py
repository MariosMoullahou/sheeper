from rest_framework import serializers
from django.db import IntegrityError
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
    mother = serializers.SlugRelatedField(
        slug_field='earing',
        queryset=Sheep.objects.all(),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Sheep
        fields = ["id", "earing", "birthdate", "gender", "mother", "is_active"]


class BirthEventSerializer(serializers.ModelSerializer):
    mother = serializers.SlugRelatedField(
        slug_field='earing',
        queryset=Sheep.objects.all(),
    )
    lambs = serializers.SlugRelatedField(
        slug_field='earing',
        queryset=Sheep.objects.all(),
        many=True,
        required=False,
    )
    # Write-only: list of {earing, gender} for lambs that don't exist yet
    new_lambs = serializers.ListField(
        child=serializers.DictField(child=serializers.CharField(allow_blank=True)),
        write_only=True,
        required=False,
        default=[],
    )

    class Meta:
        model = BirthEvent
        fields = ["id", "mother", "date", "notes", "lambs", "new_lambs"]

    def validate_new_lambs(self, value):
        """Check for empty earings and duplicates within the request."""
        earings = []
        for lamb_data in value:
            earing = lamb_data.get('earing', '').strip()
            if not earing:
                continue
            if earing in earings:
                raise serializers.ValidationError(
                    f"Duplicate lamb earing '{earing}'."
                )
            earings.append(earing)
        return value

    def validate(self, data):
        """Check new lamb earings don't already exist in the farm."""
        mother = data.get('mother')
        new_lambs = data.get('new_lambs', [])
        if mother and new_lambs:
            farm = mother.farm
            for lamb_data in new_lambs:
                earing = lamb_data.get('earing', '').strip()
                if earing and Sheep.objects.filter(farm=farm, earing=earing).exists():
                    raise serializers.ValidationError({
                        'new_lambs': f"Sheep with earing '{earing}' already exists in this farm."
                    })
        return data

    def create(self, validated_data):
        new_lamb_earings = validated_data.pop('new_lambs', [])
        existing_lambs = validated_data.pop('lambs', [])
        farm = validated_data['mother'].farm

        birth_event = BirthEvent.objects.create(**validated_data)

        # Add existing lambs
        for lamb in existing_lambs:
            lamb.mother = birth_event.mother
            lamb.save(update_fields=['mother'])
            birth_event.lambs.add(lamb)

        # Create new lambs and add them
        for lamb_data in new_lamb_earings:
            earing = lamb_data.get('earing', '').strip()
            gender = lamb_data.get('gender', '').strip()
            if earing:
                lamb = Sheep.objects.create(
                    earing=earing,
                    farm=farm,
                    mother=birth_event.mother,
                    birthdate=birth_event.date,
                    gender=gender if gender in ('M', 'F') else 'U',
                )
                birth_event.lambs.add(lamb)

        return birth_event


class CalendarEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = CalendarEvent
        fields = ["id", "title", "start", "end", "group_id", "color"]
