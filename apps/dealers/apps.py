from django.apps import AppConfig


class DealersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.dealers'
    verbose_name = 'Dealers'

    def ready(self):
        """Register signal handlers when app is ready."""
        import apps.dealers.models  # noqa
