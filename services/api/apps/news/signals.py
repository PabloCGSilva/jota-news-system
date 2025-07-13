"""
Signals for news app.
"""
from django.db.models.signals import post_save, post_delete, m2m_changed
from django.dispatch import receiver
from django.core.cache import cache
from django.utils import timezone
from .models import News, Tag, Category, Subcategory


@receiver(post_save, sender=News)
def news_post_save(sender, instance, created, **kwargs):
    """
    Handle post save signal for News model.
    """
    # Clear related caches
    cache.delete(f"category_stats_{instance.category.id}")
    if instance.subcategory:
        cache.delete(f"subcategory_stats_{instance.subcategory.id}")
    
    # If news is created, trigger classification if not already classified
    if created and not instance.is_processed:
        from apps.classification.tasks import classify_news
        classify_news.delay(instance.id)
    
    # If news is marked as urgent, trigger notification
    if instance.is_urgent and not created:
        from apps.notifications.tasks import send_urgent_notification
        send_urgent_notification.delay(instance.id)


@receiver(post_delete, sender=News)
def news_post_delete(sender, instance, **kwargs):
    """
    Handle post delete signal for News model.
    """
    # Clear related caches
    cache.delete(f"category_stats_{instance.category.id}")
    if instance.subcategory:
        cache.delete(f"subcategory_stats_{instance.subcategory.id}")


@receiver(m2m_changed, sender=News.tags.through)
def news_tags_changed(sender, instance, action, pk_set, **kwargs):
    """
    Handle changes to news tags.
    """
    if action in ['post_add', 'post_remove']:
        # Update tag usage counts
        if pk_set:
            tags = Tag.objects.filter(pk__in=pk_set)
            for tag in tags:
                tag.usage_count = tag.news.count()
                tag.save(update_fields=['usage_count'])


@receiver(post_save, sender=Category)
def category_post_save(sender, instance, created, **kwargs):
    """
    Handle post save signal for Category model.
    """
    # Clear category stats cache
    cache.delete(f"category_stats_{instance.id}")


@receiver(post_save, sender=Subcategory)
def subcategory_post_save(sender, instance, created, **kwargs):
    """
    Handle post save signal for Subcategory model.
    """
    # Clear subcategory stats cache
    cache.delete(f"subcategory_stats_{instance.id}")
    # Clear parent category stats cache
    cache.delete(f"category_stats_{instance.category.id}")


@receiver(post_save, sender=Tag)
def tag_post_save(sender, instance, created, **kwargs):
    """
    Handle post save signal for Tag model.
    """
    # Clear tag-related caches if needed
    pass