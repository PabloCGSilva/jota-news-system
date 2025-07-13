"""
App configuration for notifications app.
"""
from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    """Configuration for notifications app."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.notifications'
    verbose_name = 'Notification System'
    
    def ready(self):
        """Import signals when app is ready."""
        import apps.notifications.signals