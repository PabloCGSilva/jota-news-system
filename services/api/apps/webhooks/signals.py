"""
Signals for webhook app.
"""
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from .models import WebhookSource, WebhookLog


@receiver(post_save, sender=WebhookSource)
def webhook_source_post_save(sender, instance, created, **kwargs):
    """
    Handle post save signal for WebhookSource model.
    """
    # Clear related caches
    cache.delete(f"webhook_source_{instance.id}")
    cache.delete("webhook_sources_active")
    
    # Log the event
    import logging
    logger = logging.getLogger(__name__)
    
    action = 'created' if created else 'updated'
    logger.info(f"Webhook source {action}: {instance.name}")


@receiver(post_delete, sender=WebhookSource)
def webhook_source_post_delete(sender, instance, **kwargs):
    """
    Handle post delete signal for WebhookSource model.
    """
    # Clear related caches
    cache.delete(f"webhook_source_{instance.id}")
    cache.delete("webhook_sources_active")
    
    # Log the event
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Webhook source deleted: {instance.name}")


@receiver(post_save, sender=WebhookLog)
def webhook_log_post_save(sender, instance, created, **kwargs):
    """
    Handle post save signal for WebhookLog model.
    """
    if created:
        # Clear dashboard cache
        cache.delete("webhook_dashboard_stats")
        
        # Log the event for monitoring
        import logging
        logger = logging.getLogger(__name__)
        logger.info(
            f"Webhook log created: {instance.source.name} - {instance.status}",
            extra={
                'webhook_source': instance.source.name,
                'webhook_status': instance.status,
                'webhook_method': instance.method,
                'webhook_ip': instance.remote_ip,
                'correlation_id': instance.correlation_id
            }
        )
    
    # Update source statistics if status changed
    if not created and instance.status in ['success', 'failed']:
        # This could trigger a task to update statistics
        pass