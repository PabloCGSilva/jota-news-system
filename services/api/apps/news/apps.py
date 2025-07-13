"""
App configuration for news app.
"""
from django.apps import AppConfig


class NewsConfig(AppConfig):
    """Configuration for news app."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.news'
    verbose_name = 'News Management'
    
    def ready(self):
        """Import signals when app is ready."""
        import apps.news.signals