"""
App configuration for classification app.
"""
from django.apps import AppConfig


class ClassificationConfig(AppConfig):
    """Configuration for classification app."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.classification'
    verbose_name = 'News Classification'
    
    def ready(self):
        """Import signals when app is ready."""
        import apps.classification.signals