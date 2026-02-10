from django.apps import AppConfig


class ClinicaConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'clinica'

    def ready(self):
        # import signal handlers
        try:
            import clinica.signals  # noqa: F401
        except Exception:
            pass
