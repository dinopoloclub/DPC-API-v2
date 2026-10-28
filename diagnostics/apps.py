"""App configuration."""

from django.apps import AppConfig


class DiagnosticsConfig(AppConfig):
    """The diagnostics app"""

    name = "diagnostics"
    default_auto_field = "django.db.models.BigAutoField"
