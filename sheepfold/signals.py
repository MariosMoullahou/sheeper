from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender='sheepfold.Milk')
def recalculate_on_milk_save(sender, instance, **kwargs):
    from .services import assign_groups
    assign_groups(instance.sheep.farm)


@receiver(post_save, sender='accounts.Farm')
def create_milk_settings_for_farm(sender, instance, created, **kwargs):
    if created:
        from .models import FarmMilkSettings
        FarmMilkSettings.objects.get_or_create(farm=instance)
