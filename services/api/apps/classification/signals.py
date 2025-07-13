"""
Signals for classification app.
"""
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from .models import ClassificationRule, ClassificationModel, ClassificationResult


@receiver(post_save, sender=ClassificationRule)
def classification_rule_post_save(sender, instance, created, **kwargs):
    """
    Handle post save signal for ClassificationRule model.
    """
    # Clear classification cache
    cache.delete("classification_rules_active")
    cache.delete(f"classification_rule_{instance.id}")
    
    # Log the event
    import logging
    logger = logging.getLogger(__name__)
    
    action = 'created' if created else 'updated'
    logger.info(f"Classification rule {action}: {instance.name}")


@receiver(post_delete, sender=ClassificationRule)
def classification_rule_post_delete(sender, instance, **kwargs):
    """
    Handle post delete signal for ClassificationRule model.
    """
    # Clear classification cache
    cache.delete("classification_rules_active")
    cache.delete(f"classification_rule_{instance.id}")
    
    # Log the event
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Classification rule deleted: {instance.name}")


@receiver(post_save, sender=ClassificationModel)
def classification_model_post_save(sender, instance, created, **kwargs):
    """
    Handle post save signal for ClassificationModel model.
    """
    # Clear model cache
    cache.delete("classification_models_active")
    cache.delete(f"classification_model_{instance.id}")
    
    # Log the event
    import logging
    logger = logging.getLogger(__name__)
    
    action = 'created' if created else 'updated'
    logger.info(f"Classification model {action}: {instance.name}")


@receiver(post_save, sender=ClassificationResult)
def classification_result_post_save(sender, instance, created, **kwargs):
    """
    Handle post save signal for ClassificationResult model.
    """
    if created:
        # Clear dashboard cache
        cache.delete("classification_dashboard_stats")
        
        # Update rule statistics if applicable
        if instance.applied_rule:
            instance.applied_rule.increment_matches()
        
        # Update model statistics if applicable
        if instance.applied_model:
            instance.applied_model.increment_predictions()
        
        # Log the event for monitoring
        import logging
        logger = logging.getLogger(__name__)
        logger.info(
            f"Classification result created: {instance.news.title} -> {instance.predicted_category.name}",
            extra={
                'classification_method': instance.method,
                'predicted_category': instance.predicted_category.name,
                'confidence': instance.category_confidence,
                'is_accepted': instance.is_accepted,
                'processing_time': instance.processing_time
            }
        )