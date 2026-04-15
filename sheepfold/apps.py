from django.apps import AppConfig


class SheepfoldConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'sheepfold'

    def ready(self):
        import sheepfold.signals  # noqa: F401
