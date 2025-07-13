"""
App configuration for webhooks app.
"""
from django.apps import AppConfig


class WebhooksConfig(AppConfig):
    """Configuration for webhooks app."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.webhooks'
    verbose_name = 'Webhook Management'
    
    def ready(self):
        """Import signals when app is ready."""
        import apps.webhooks.signals