"""
Signals for notifications app.
"""
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from .models import NotificationChannel, NotificationSubscription, Notification


@receiver(post_save, sender=NotificationChannel)
def notification_channel_post_save(sender, instance, created, **kwargs):
    """
    Handle post save signal for NotificationChannel model.
    """
    # Clear related caches
    cache.delete("notification_channels_active")
    cache.delete(f"notification_channel_{instance.id}")
    
    # Log the event
    import logging
    logger = logging.getLogger(__name__)
    
    action = 'created' if created else 'updated'
    logger.info(f"Notification channel {action}: {instance.name}")


@receiver(post_delete, sender=NotificationChannel)
def notification_channel_post_delete(sender, instance, **kwargs):
    """
    Handle post delete signal for NotificationChannel model.
    """
    # Clear related caches
    cache.delete("notification_channels_active")
    cache.delete(f"notification_channel_{instance.id}")
    
    # Log the event
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Notification channel deleted: {instance.name}")


@receiver(post_save, sender=NotificationSubscription)
def notification_subscription_post_save(sender, instance, created, **kwargs):
    """
    Handle post save signal for NotificationSubscription model.
    """
    if created:
        # Clear subscription cache
        cache.delete(f"user_subscriptions_{instance.user.id}")
        
        # Log the event
        import logging
        logger = logging.getLogger(__name__)
        logger.info(
            f"New notification subscription: {instance.user.username} -> {instance.channel.name}",
            extra={
                'user_id': instance.user.id,
                'channel_name': instance.channel.name,
                'destination': instance.destination,
                'min_priority': instance.min_priority
            }
        )


@receiver(post_save, sender=Notification)
def notification_post_save(sender, instance, created, **kwargs):
    """
    Handle post save signal for Notification model.
    """
    if created:
        # Clear dashboard cache
        cache.delete("notification_dashboard_stats")
        
        # Log the event for monitoring
        import logging
        logger = logging.getLogger(__name__)
        logger.info(
            f"Notification created: {instance.subscription.user.username} via {instance.subscription.channel.name}",
            extra={
                'notification_id': str(instance.id),
                'user_id': instance.subscription.user.id,
                'channel_name': instance.subscription.channel.name,
                'priority': instance.priority,
                'status': instance.status,
                'scheduled_for': instance.scheduled_for.isoformat() if instance.scheduled_for else None
            }
        )
    
    # Log status changes
    if not created and instance.status in ['sent', 'delivered', 'failed']:
        import logging
        logger = logging.getLogger(__name__)
        logger.info(
            f"Notification status changed: {instance.id} -> {instance.status}",
            extra={
                'notification_id': str(instance.id),
                'status': instance.status,
                'external_id': instance.external_id,
                'error_message': instance.error_message if instance.status == 'failed' else None
            }
        )