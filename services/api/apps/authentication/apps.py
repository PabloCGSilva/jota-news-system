"""
Authentication app configuration for JOTA News System.
"""
from django.apps import AppConfig


class AuthenticationConfig(AppConfig):
    """Authentication app configuration."""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.authentication'
    verbose_name = 'Authentication'
    
    def ready(self):
        """App ready callback."""
        # Import signals if any
        try:
            from . import signals
        except ImportError:
            pass