from django.apps import AppConfig


class VaultConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "vault"
    verbose_name = "Vault"

    def ready(self):
        from . import signals  # noqa: F401
