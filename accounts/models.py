import uuid
from django.db import models
from django.conf import settings

ROLE_FARMER = 'farmer'
ROLE_ANALYST = 'analyst'
ROLE_MANAGER = 'manager'

ROLE_CHOICES = [
    (ROLE_FARMER, 'Farmer'),
    (ROLE_ANALYST, 'Analyst'),
    (ROLE_MANAGER, 'Manager'),
]


class Farm(models.Model):
    name = models.CharField(max_length=200)
    calendar_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='farms',
        blank=True,
    )

    def __str__(self):
        return self.name


class Profile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile',
    )
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default=ROLE_FARMER,
    )

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"
