from django.conf import settings
from rest_framework import serializers
from .models import Milk, Sheep, BirthEvent, HealthRecord, CalendarEvent, MilkAnalysis


class MilkSerializer(serializers.ModelSerializer):
    # Accept earing on write, show earing on read
    sheep = serializers.SlugRelatedField(
        slug_field='earing',
        queryset=Sheep.objects.all(),
    )

    class Meta:
        model = Milk
        fields = ["id", "sheep", "date", "milk", "is_active"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        farm = self.context.get('farm')
        if farm:
            self.fields['sheep'].queryset = Sheep.objects.filter(farm=farm)

    def validate_sheep(self, sheep):
        if sheep.gender == 'M':
            raise serializers.ValidationError("Milk measurements cannot be recorded for male sheep (rams).")
        return sheep


class SheepData(serializers.ModelSerializer):
    mother = serializers.SlugRelatedField(
        slug_field='earing',
        queryset=Sheep.objects.all(),
        required=False,
        allow_null=True,
    )
    father = serializers.SlugRelatedField(
        slug_field='earing',
        queryset=Sheep.objects.all(),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Sheep
        fields = ["id", "earing", "birthdate", "gender", "mother", "father", "is_active", "group", "ready_for_birth"]

    def validate_mother(self, mother):
        farm = self.context.get('farm')
        if farm and mother and mother.farm_id != farm.pk:
            raise serializers.ValidationError("Mother does not belong to your farm.")
        return mother

    def validate_father(self, father):
        farm = self.context.get('farm')
        if farm and father and father.farm_id != farm.pk:
            raise serializers.ValidationError("Father does not belong to your farm.")
        if father and father.gender == 'F':
            raise serializers.ValidationError("Father must be male.")
        return father


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
    father = serializers.SlugRelatedField(
        slug_field='earing',
        queryset=Sheep.objects.all(),
        required=False,
        allow_null=True,
        write_only=True,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        farm = self.context.get('farm')
        if farm:
            self.fields['mother'].queryset = Sheep.objects.filter(farm=farm)
            self.fields['lambs'].queryset = Sheep.objects.filter(farm=farm)
            self.fields['father'].queryset = Sheep.objects.filter(farm=farm)

    # Write-only: list of {earing, gender} for lambs that don't exist yet
    new_lambs = serializers.ListField(
        child=serializers.DictField(child=serializers.CharField(allow_blank=True)),
        write_only=True,
        required=False,
        default=[],
    )

    class Meta:
        model = BirthEvent
        fields = ["id", "mother", "date", "notes", "lambs", "new_lambs", "father"]

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
        """Check farm ownership, father gender, and new lamb earing uniqueness."""
        farm = self.context.get('farm')
        mother = data.get('mother')
        father = data.get('father')

        # Validate father is male
        if father and father.gender == 'F':
            raise serializers.ValidationError({
                'father': "Father must be male."
            })

        # Validate mother belongs to active farm
        if farm and mother and mother.farm_id != farm.pk:
            raise serializers.ValidationError({
                'mother': "This sheep does not belong to your farm."
            })

        # Validate existing lambs belong to active farm
        lambs = data.get('lambs', [])
        for lamb in lambs:
            if farm and lamb.farm_id != farm.pk:
                raise serializers.ValidationError({
                    'lambs': f"Sheep '{lamb.earing}' does not belong to your farm."
                })

        # Check new lamb earings don't already exist in the farm
        new_lambs = data.get('new_lambs', [])
        if mother and new_lambs:
            check_farm = farm or mother.farm
            for lamb_data in new_lambs:
                earing = lamb_data.get('earing', '').strip()
                if earing and Sheep.objects.filter(farm=check_farm, earing=earing).exists():
                    raise serializers.ValidationError({
                        'new_lambs': f"Sheep with earing '{earing}' already exists in this farm."
                    })
        return data

    def create(self, validated_data):
        new_lamb_earings = validated_data.pop('new_lambs', [])
        existing_lambs = validated_data.pop('lambs', [])
        father = validated_data.pop('father', None)
        farm = validated_data['mother'].farm

        birth_event = BirthEvent.objects.create(**validated_data)

        # Add existing lambs — set mother and father
        for lamb in existing_lambs:
            lamb.mother = birth_event.mother
            if father:
                lamb.father = father
                lamb.save(update_fields=['mother', 'father'])
            else:
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
                    father=father,
                    birthdate=birth_event.date,
                    gender=gender if gender in ('M', 'F') else 'U',
                )
                birth_event.lambs.add(lamb)

        return birth_event


class HealthRecordSerializer(serializers.ModelSerializer):
    sheep = serializers.SlugRelatedField(
        slug_field='earing',
        queryset=Sheep.objects.all(),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = HealthRecord
        fields = [
            "id", "sheep", "is_batch", "date", "record_type",
            "title", "notes", "next_due", "is_active",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        farm = self.context.get('farm')
        if farm:
            self.fields['sheep'].queryset = Sheep.objects.filter(farm=farm)

    def validate(self, data):
        is_batch = data.get('is_batch', False)
        sheep = data.get('sheep')
        if not is_batch and not sheep:
            raise serializers.ValidationError({
                'sheep': 'Sheep is required for individual records.'
            })
        if is_batch:
            data['sheep'] = None
        return data

    def create(self, validated_data):
        record = super().create(validated_data)

        # Auto-create calendar reminder when next_due is set
        if record.next_due and record.farm:
            target = 'All Sheep' if record.is_batch else record.sheep.earing
            CalendarEvent.objects.create(
                farm=record.farm,
                title=f"{record.record_type}: {record.title} — {target}",
                start=record.next_due,
                color='#ef4444',
                group_id=f'health_{record.pk}',
            )

        return record


class CalendarEventSerializer(serializers.ModelSerializer):
    farm_name = serializers.CharField(source='farm.name', read_only=True)

    class Meta:
        model = CalendarEvent
        fields = ["id", "title", "start", "end", "group_id", "color", "farm_name"]


class MilkAnalysisSerializer(serializers.ModelSerializer):
    attachment_url = serializers.SerializerMethodField()
    attachment_name = serializers.SerializerMethodField()
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)

    class Meta:
        model = MilkAnalysis
        fields = [
            "id",
            "sampling_date", "analysis_date", "lab_name", "sample_ref",
            "protein_pct", "fat_pct", "snf_pct", "lactose_pct", "casein_pct", "water_pct",
            "freezing_point",
            "foreign_milk_pct", "antibiotics_detected", "aflatoxin_m1",
            "total_bacteria_count", "scc", "clostridia",
            "attachment", "attachment_url", "attachment_name",
            "notes",
            "created_by_username", "created_at", "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]
        extra_kwargs = {"attachment": {"write_only": True, "required": False}}

    def get_attachment_url(self, obj):
        if not obj.attachment:
            return None
        request = self.context.get('request')
        url = obj.attachment.url
        return request.build_absolute_uri(url) if request else url

    def get_attachment_name(self, obj):
        if not obj.attachment:
            return None
        return obj.attachment.name.rsplit('/', 1)[-1]

    def validate_attachment(self, file):
        if file is None:
            return file
        max_bytes = settings.MILK_ANALYSIS_MAX_UPLOAD_MB * 1024 * 1024
        if file.size > max_bytes:
            raise serializers.ValidationError(
                f"File too large (max {settings.MILK_ANALYSIS_MAX_UPLOAD_MB} MB)."
            )
        ext = file.name.rsplit('.', 1)[-1].lower() if '.' in file.name else ''
        if ext not in settings.MILK_ANALYSIS_ALLOWED_EXTENSIONS:
            raise serializers.ValidationError(
                f"File type '.{ext}' not allowed. Allowed: "
                + ", ".join(settings.MILK_ANALYSIS_ALLOWED_EXTENSIONS)
            )
        return file

    def validate(self, data):
        sampling = data.get('sampling_date') or getattr(self.instance, 'sampling_date', None)
        analysis = data.get('analysis_date') or getattr(self.instance, 'analysis_date', None)
        if sampling and analysis and analysis < sampling:
            raise serializers.ValidationError({
                'analysis_date': 'Analysis date cannot be before sampling date.'
            })
        return data
