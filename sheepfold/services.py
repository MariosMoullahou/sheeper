from datetime import timedelta
from django.utils import timezone
from django.db.models import Avg


def assign_groups(farm):
    """
    Assigns a milk-production group to every active sheep in the farm.
    Uses the farm's FarmMilkSettings for thresholds and period window.
    """
    try:
        settings = farm.milk_settings
    except Exception:
        # No settings yet — use defaults
        from .models import FarmMilkSettings
        settings = FarmMilkSettings.objects.create(farm=farm)

    cutoff = timezone.localdate() - timedelta(days=settings.period_days)

    sheep_qs = farm.sheep.filter(is_active=True).prefetch_related('milk')

    for sheep in sheep_qs:
        if sheep.gender == 'M':
            sheep.group = 'ram'
        elif sheep.ready_for_birth:
            sheep.group = 'ready'
        else:
            avg = (
                sheep.milk
                .filter(date__gte=cutoff, is_active=True)
                .aggregate(avg=Avg('milk'))['avg']
            )
            if avg is None:
                sheep.group = 'dry'
            elif avg >= settings.high_threshold:
                sheep.group = 'high'
            elif avg >= settings.med_threshold:
                sheep.group = 'med'
            elif avg >= settings.low_threshold:
                sheep.group = 'low'
            else:
                sheep.group = 'dry'

    # Bulk update for performance
    farm.sheep.filter(is_active=True).bulk_update(sheep_qs, ['group'])
