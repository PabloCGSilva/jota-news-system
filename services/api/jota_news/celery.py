"""
Celery configuration for jota_news project.
"""
import os
from celery import Celery
from django.conf import settings

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'jota_news.settings')

app = Celery('jota_news')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Import monitoring after app configuration
try:
    from .celery_monitoring import (
        task_prerun_handler, task_postrun_handler, task_success_handler,
        task_failure_handler, task_retry_handler, worker_ready_handler,
        worker_shutdown_handler
    )
    print("Celery monitoring loaded successfully")
except ImportError as e:
    print(f"Failed to load Celery monitoring: {e}")

# Celery beat schedule for periodic tasks
app.conf.beat_schedule = {
    'cleanup-old-news': {
        'task': 'apps.news.tasks.cleanup_old_news',
        'schedule': 3600.0,  # Run every hour
    },
    'update-news-statistics': {
        'task': 'apps.news.tasks.update_news_statistics',
        'schedule': 1800.0,  # Run every 30 minutes
    },
}

app.conf.timezone = 'America/Sao_Paulo'

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')