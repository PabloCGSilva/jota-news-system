"""
Celery tasks for news app.
"""
import logging
from celery import shared_task
from django.utils import timezone
from django.db.models import Count, Avg
from datetime import timedelta
from .models import News, NewsStatistic, NewsProcessingLog

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def cleanup_old_news(self):
    """
    Cleanup old news articles and processing logs.
    """
    try:
        # Delete news older than 1 year (configurable)
        cutoff_date = timezone.now() - timedelta(days=365)
        
        # Delete old processing logs first
        old_logs = NewsProcessingLog.objects.filter(created_at__lt=cutoff_date)
        logs_count = old_logs.count()
        old_logs.delete()
        
        # Optionally delete very old news (uncomment if needed)
        # old_news = News.objects.filter(created_at__lt=cutoff_date)
        # news_count = old_news.count()
        # old_news.delete()
        
        logger.info(f"Cleaned up {logs_count} old processing logs")
        
        return {
            'status': 'success',
            'logs_deleted': logs_count,
            'news_deleted': 0  # news_count if news deletion is enabled
        }
        
    except Exception as exc:
        logger.error(f"Error cleaning up old news: {exc}")
        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3)
def update_news_statistics(self):
    """
    Update daily news statistics.
    """
    try:
        today = timezone.now().date()
        
        # Get news from today
        today_news = News.objects.filter(created_at__date=today)
        
        # Calculate statistics
        total_news = today_news.count()
        urgent_news = today_news.filter(is_urgent=True).count()
        
        # Categories count
        categories_count = dict(
            today_news.values('category__name')
            .annotate(count=Count('id'))
            .values_list('category__name', 'count')
        )
        
        # Sources count
        sources_count = dict(
            today_news.values('source')
            .annotate(count=Count('id'))
            .values_list('source', 'count')
        )
        
        # Average processing time
        avg_processing_time = NewsProcessingLog.objects.filter(
            created_at__date=today,
            status='success'
        ).aggregate(avg_time=Avg('processing_time'))['avg_time'] or 0.0
        
        # Update or create statistics
        statistic, created = NewsStatistic.objects.update_or_create(
            date=today,
            defaults={
                'total_news': total_news,
                'urgent_news': urgent_news,
                'categories_count': categories_count,
                'sources_count': sources_count,
                'avg_processing_time': avg_processing_time,
            }
        )
        
        action = 'created' if created else 'updated'
        logger.info(f"News statistics {action} for {today}")
        
        return {
            'status': 'success',
            'date': str(today),
            'total_news': total_news,
            'urgent_news': urgent_news,
            'action': action
        }
        
    except Exception as exc:
        logger.error(f"Error updating news statistics: {exc}")
        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3)
def update_tag_usage_counts(self):
    """
    Update tag usage counts.
    """
    try:
        from .models import Tag
        
        updated_count = 0
        
        for tag in Tag.objects.all():
            old_count = tag.usage_count
            new_count = tag.news.count()
            
            if old_count != new_count:
                tag.usage_count = new_count
                tag.save(update_fields=['usage_count'])
                updated_count += 1
        
        logger.info(f"Updated usage counts for {updated_count} tags")
        
        return {
            'status': 'success',
            'updated_tags': updated_count
        }
        
    except Exception as exc:
        logger.error(f"Error updating tag usage counts: {exc}")
        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3)
def generate_news_summary(self, news_id):
    """
    Generate summary for a news article if not provided.
    """
    try:
        news = News.objects.get(id=news_id)
        
        if not news.summary and news.content:
            # Simple summary generation (first 500 characters)
            # In a real implementation, you might use NLP libraries
            summary = news.content[:497] + '...' if len(news.content) > 500 else news.content
            
            news.summary = summary
            news.save(update_fields=['summary'])
            
            logger.info(f"Generated summary for news: {news.title}")
            
            return {
                'status': 'success',
                'news_id': str(news_id),
                'summary_length': len(summary)
            }
        
        return {
            'status': 'skipped',
            'news_id': str(news_id),
            'reason': 'Summary already exists or no content'
        }
        
    except News.DoesNotExist:
        logger.error(f"News with ID {news_id} not found")
        return {
            'status': 'error',
            'news_id': str(news_id),
            'error': 'News not found'
        }
    except Exception as exc:
        logger.error(f"Error generating summary for news {news_id}: {exc}")
        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3)
def bulk_process_news(self, news_ids):
    """
    Process multiple news articles in bulk.
    """
    try:
        processed_count = 0
        errors = []
        
        for news_id in news_ids:
            try:
                news = News.objects.get(id=news_id)
                
                if not news.is_processed:
                    # Trigger classification
                    from apps.classification.tasks import classify_news
                    classify_news.delay(news_id)
                    
                    # Generate summary if needed
                    if not news.summary:
                        generate_news_summary.delay(news_id)
                    
                    processed_count += 1
                    
            except News.DoesNotExist:
                errors.append(f"News {news_id} not found")
            except Exception as e:
                errors.append(f"Error processing news {news_id}: {str(e)}")
        
        logger.info(f"Bulk processed {processed_count} news articles")
        
        return {
            'status': 'success',
            'processed_count': processed_count,
            'errors': errors
        }
        
    except Exception as exc:
        logger.error(f"Error in bulk processing: {exc}")
        raise self.retry(exc=exc, countdown=60)