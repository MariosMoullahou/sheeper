from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone


GROUP_CHOICES = [
    ('high',  'High'),
    ('med',   'Med'),
    ('low',   'Low'),
    ('dry',   'Dry'),
    ('ram',   'Ram'),
    ('ready', 'Ready for Birth'),
]


class FarmMilkSettings(models.Model):
    farm = models.OneToOneField(
        'accounts.Farm',
        on_delete=models.CASCADE,
        related_name='milk_settings',
    )
    period_days     = models.PositiveIntegerField(default=30)
    high_threshold  = models.DecimalField(max_digits=5, decimal_places=2, default=2.00)
    med_threshold   = models.DecimalField(max_digits=5, decimal_places=2, default=1.00)
    low_threshold   = models.DecimalField(max_digits=5, decimal_places=2, default=0.50)

    def __str__(self):
        return f"Milk settings — {self.farm.name}"


class Sheep(models.Model):
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('U', 'Unknown'),
    ]

    farm = models.ForeignKey(
        'accounts.Farm',
        on_delete=models.CASCADE,
        related_name='sheep',
    )
    earing = models.CharField(max_length=100)
    birthdate = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, default='U')
    mother = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='children',
    )
    father = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='sired',
    )
    is_active = models.BooleanField(default=True)
    group = models.CharField(max_length=20, choices=GROUP_CHOICES, blank=True, default='')
    ready_for_birth = models.BooleanField(default=False)

    class Meta:
        unique_together = ['farm', 'earing']

    def clean(self):
        if self.mother and self.mother.gender == 'M':
            raise ValidationError({'mother': 'Mother must be female.'})
        if self.father and self.father.gender == 'F':
            raise ValidationError({'father': 'Father must be male.'})

    def __str__(self):
        return self.earing


class BirthEvent(models.Model):
    mother = models.ForeignKey(Sheep, on_delete=models.CASCADE, related_name='birth_events')
    date = models.DateField()
    notes = models.TextField(blank=True)
    lambs = models.ManyToManyField(Sheep, related_name='birth_event', blank=True)

    def clean(self):
        if self.mother and self.mother.gender == 'M':
            raise ValidationError({'mother': 'Mother must be female.'})

    def __str__(self):
        return f"Birth by {self.mother.earing} on {self.date}"


class Milk(models.Model):
    sheep = models.ForeignKey(
        Sheep,
        on_delete=models.CASCADE,
        related_name='milk',
    )
    date = models.DateField(default=timezone.localdate)
    milk = models.DecimalField(max_digits=5, decimal_places=2, help_text="liter")
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.sheep.earing} - {self.date} ({self.milk} liter)"


class HealthRecord(models.Model):
    farm = models.ForeignKey(
        'accounts.Farm',
        on_delete=models.CASCADE,
        related_name='health_records',
    )
    sheep = models.ForeignKey(
        Sheep,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='health_records',
    )
    is_batch = models.BooleanField(default=False)
    date = models.DateField()
    record_type = models.CharField(max_length=100)
    title = models.CharField(max_length=200)
    notes = models.TextField(blank=True)
    next_due = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        target = 'All Sheep' if self.is_batch else (self.sheep.earing if self.sheep else 'Unknown')
        return f"{self.record_type}: {self.title} — {target} ({self.date})"


class MilkAnalysis(models.Model):
    """Bulk-tank lab analysis results — one row per farm sampling."""
    farm = models.ForeignKey(
        'accounts.Farm',
        on_delete=models.CASCADE,
        related_name='milk_analyses',
    )
    sampling_date = models.DateField()
    analysis_date = models.DateField(null=True, blank=True)
    lab_name = models.CharField(max_length=200, blank=True)
    sample_ref = models.CharField(max_length=100, blank=True)

    # Composition (percentages)
    protein_pct = models.DecimalField(max_digits=6, decimal_places=3, null=True, blank=True)
    fat_pct = models.DecimalField(max_digits=6, decimal_places=3, null=True, blank=True)
    snf_pct = models.DecimalField(max_digits=6, decimal_places=3, null=True, blank=True)
    lactose_pct = models.DecimalField(max_digits=6, decimal_places=3, null=True, blank=True)
    casein_pct = models.DecimalField(max_digits=6, decimal_places=3, null=True, blank=True)
    water_pct = models.DecimalField(max_digits=6, decimal_places=3, null=True, blank=True)

    # Physical
    freezing_point = models.DecimalField(max_digits=6, decimal_places=4, null=True, blank=True)

    # Adulteration / contamination
    foreign_milk_pct = models.DecimalField(max_digits=6, decimal_places=3, null=True, blank=True)
    antibiotics_detected = models.BooleanField(null=True, blank=True)
    aflatoxin_m1 = models.DecimalField(max_digits=8, decimal_places=3, null=True, blank=True)

    # Microbiology
    total_bacteria_count = models.BigIntegerField(null=True, blank=True)
    scc = models.BigIntegerField(null=True, blank=True)
    clostridia = models.BigIntegerField(null=True, blank=True)

    attachment = models.FileField(upload_to='milk_analyses/%Y/%m/', null=True, blank=True)
    notes = models.TextField(blank=True)

    created_by = models.ForeignKey(
        'auth.User',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='milk_analyses_uploaded',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-sampling_date', '-id']
        indexes = [
            models.Index(fields=['farm', '-sampling_date']),
        ]

    def __str__(self):
        return f"{self.farm.name} — {self.sampling_date}"


class CalendarEvent(models.Model):
    farm = models.ForeignKey(
        'accounts.Farm',
        on_delete=models.CASCADE,
        related_name='calendar_events',
    )
    title = models.CharField(max_length=255)
    start = models.DateField()
    end = models.DateTimeField(null=True, blank=True)
    group_id = models.CharField(max_length=100, blank=True, db_index=True)
    color = models.CharField(max_length=50, blank=True)

    def __str__(self):
        return self.title
