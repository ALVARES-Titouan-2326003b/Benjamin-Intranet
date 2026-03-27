from django.apps import AppConfig

class AuthenticationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'authentication'

    def ready(self):
        # Ensure signal handlers are connected when app is loaded
        from . import signals  # noqa: F401

