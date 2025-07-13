"""
Celery tasks for webhook processing.
"""
import json
import logging
import time
from celery import shared_task
from django.utils import timezone
from django.db import transaction
from django.db.models import Count, Avg, Sum

from .models import WebhookLog, WebhookSource, WebhookStatistic
from .utils import (
    validate_webhook_data, extract_category_hints, prepare_news_data,
    create_processing_log, send_webhook_notification
)

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def process_webhook_async(self, webhook_log_id):
    """
    Process webhook asynchronously.
    """
    start_time = time.time()
    
    try:
        # Get webhook log
        webhook_log = WebhookLog.objects.get(id=webhook_log_id)
        webhook_log.status = 'processing'
        webhook_log.save()
        
        # Parse webhook data
        try:
            webhook_data = json.loads(webhook_log.body)
        except json.JSONDecodeError as e:
            webhook_log.set_invalid(f"Invalid JSON: {str(e)}")
            webhook_log.source.increment_failed_requests()
            return {'status': 'error', 'error': 'Invalid JSON'}
        
        # Validate webhook data
        validation_errors = validate_webhook_data(webhook_data, webhook_log.source)
        if validation_errors:
            error_message = "; ".join(validation_errors)
            webhook_log.set_invalid(error_message)
            webhook_log.source.increment_failed_requests()
            return {'status': 'error', 'error': error_message}
        
        # Check for duplicate external_id
        external_id = webhook_data.get('external_id')
        if external_id:
            from apps.news.models import News
            if News.objects.filter(external_id=external_id).exists():
                webhook_log.set_invalid("News with this external_id already exists")
                webhook_log.source.increment_failed_requests()
                return {'status': 'error', 'error': 'Duplicate external_id'}
        
        # Prepare news data
        news_data = prepare_news_data(webhook_data, webhook_log.source)
        
        # Extract category hints
        category_hints = extract_category_hints(webhook_data)
        
        # Create news article
        with transaction.atomic():
            from apps.news.models import News, Category, Subcategory, Tag
            
            # Try to find category from hints
            category = None
            if category_hints.get('category'):
                try:
                    category = Category.objects.get(
                        name__iexact=category_hints['category'],
                        is_active=True
                    )
                except Category.DoesNotExist:
                    pass
            
            # Default to a general category if not found
            if not category:
                category, _ = Category.objects.get_or_create(
                    name='Geral',
                    defaults={
                        'slug': 'geral',
                        'description': 'Categoria geral para notícias não classificadas'
                    }
                )
            
            news_data['category'] = category
            
            # Try to find subcategory
            if category_hints.get('subcategory'):
                try:
                    subcategory = Subcategory.objects.get(
                        name__iexact=category_hints['subcategory'],
                        category=category,
                        is_active=True
                    )
                    news_data['subcategory'] = subcategory
                except Subcategory.DoesNotExist:
                    pass
            
            # Create news
            news = News.objects.create(**news_data)
            
            # Add tags if provided
            if webhook_data.get('tags'):
                tags = []
                for tag_name in webhook_data['tags']:
                    tag, created = Tag.objects.get_or_create(
                        name=tag_name,
                        defaults={'slug': tag_name.lower().replace(' ', '-')}
                    )
                    tags.append(tag)
                news.tags.set(tags)
            
            # Create processing log
            processing_time = time.time() - start_time
            create_processing_log(
                news=news,
                stage='webhook_received',
                status='success',
                message=f"News created from webhook: {webhook_log.source.name}",
                processing_time=processing_time
            )
            
            # Update webhook log
            webhook_log.set_success(
                news_id=news.id,
                response_data={'news_id': str(news.id), 'title': news.title}
            )
            webhook_log.processing_time = processing_time
            webhook_log.save()
            
            # Update source statistics
            webhook_log.source.increment_successful_requests()
            
            # Send notification
            send_webhook_notification(webhook_log, news)
            
            # Trigger classification if not already processed
            if not news.is_processed:
                from apps.classification.tasks import classify_news
                classify_news.delay(news.id)
            
            # Trigger urgent notification if needed
            if news.is_urgent:
                from apps.notifications.tasks import send_urgent_notification
                send_urgent_notification.delay(news.id)
            
            logger.info(f"Successfully processed webhook {webhook_log_id}, created news {news.id}")
            
            return {
                'status': 'success',
                'news_id': str(news.id),
                'title': news.title,
                'processing_time': processing_time
            }
            
    except Exception as exc:
        logger.error(f"Error processing webhook {webhook_log_id}: {str(exc)}", exc_info=True)
        
        # Update webhook log
        try:
            webhook_log = WebhookLog.objects.get(id=webhook_log_id)
            webhook_log.set_failed(str(exc), 500)
            webhook_log.source.increment_failed_requests()
        except:
            pass
        
        # Retry with exponential backoff
        countdown = 60 * (2 ** self.request.retries)
        raise self.retry(exc=exc, countdown=countdown)


@shared_task(bind=True, max_retries=3)
def update_webhook_statistics(self):
    """
    Update daily webhook statistics.
    """
    try:
        today = timezone.now().date()
        
        # Get all webhook sources
        sources = WebhookSource.objects.all()
        
        for source in sources:
            # Get logs for today
            today_logs = WebhookLog.objects.filter(
                source=source,
                created_at__date=today
            )
            
            # Calculate statistics
            total_requests = today_logs.count()
            successful_requests = today_logs.filter(status='success').count()
            failed_requests = today_logs.filter(status='failed').count()
            invalid_requests = today_logs.filter(status='invalid').count()
            
            # Average processing time
            avg_processing_time = today_logs.filter(
                processing_time__isnull=False
            ).aggregate(avg=Avg('processing_time'))['avg'] or 0.0
            
            # Count of news created
            news_created = today_logs.filter(
                status='success',
                created_news_id__isnull=False
            ).count()
            
            # Update or create statistics
            statistic, created = WebhookStatistic.objects.update_or_create(
                date=today,
                source=source,
                defaults={
                    'total_requests': total_requests,
                    'successful_requests': successful_requests,
                    'failed_requests': failed_requests,
                    'invalid_requests': invalid_requests,
                    'avg_processing_time': avg_processing_time,
                    'news_created': news_created,
                }
            )
            
            action = 'created' if created else 'updated'
            logger.info(f"Webhook statistics {action} for {source.name} on {today}")
        
        return {
            'status': 'success',
            'date': str(today),
            'sources_updated': sources.count()
        }
        
    except Exception as exc:
        logger.error(f"Error updating webhook statistics: {str(exc)}", exc_info=True)
        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3)
def cleanup_old_webhook_logs(self, days=30):
    """
    Clean up old webhook logs.
    """
    try:
        from django.utils import timezone
        
        cutoff_date = timezone.now() - timezone.timedelta(days=days)
        
        # Delete old logs
        deleted_count = WebhookLog.objects.filter(
            created_at__lt=cutoff_date
        ).delete()[0]
        
        logger.info(f"Cleaned up {deleted_count} old webhook logs")
        
        return {
            'status': 'success',
            'deleted_count': deleted_count
        }
        
    except Exception as exc:
        logger.error(f"Error cleaning up webhook logs: {str(exc)}", exc_info=True)
        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3)
def retry_failed_webhooks(self):
    """
    Retry processing of failed webhooks.
    """
    try:
        # Get failed webhooks from last 24 hours
        since = timezone.now() - timezone.timedelta(hours=24)
        failed_logs = WebhookLog.objects.filter(
            status='failed',
            created_at__gte=since
        )
        
        retry_count = 0
        
        for log in failed_logs:
            # Check if we haven't exceeded retry limit
            if log.retries.count() < 3:
                # Reset status and retry
                log.status = 'pending'
                log.save()
                
                # Process asynchronously
                process_webhook_async.delay(log.id)
                retry_count += 1
        
        logger.info(f"Initiated retry for {retry_count} failed webhooks")
        
        return {
            'status': 'success',
            'retry_count': retry_count
        }
        
    except Exception as exc:
        logger.error(f"Error retrying failed webhooks: {str(exc)}", exc_info=True)
        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3)
def process_bulk_webhooks(self, webhook_log_ids):
    """
    Process multiple webhooks in bulk.
    """
    try:
        processed_count = 0
        errors = []
        
        for webhook_log_id in webhook_log_ids:
            try:
                result = process_webhook_async.delay(webhook_log_id)
                processed_count += 1
            except Exception as e:
                errors.append(f"Error processing webhook {webhook_log_id}: {str(e)}")
        
        logger.info(f"Bulk processed {processed_count} webhooks")
        
        return {
            'status': 'success',
            'processed_count': processed_count,
            'errors': errors
        }
        
    except Exception as exc:
        logger.error(f"Error in bulk webhook processing: {str(exc)}", exc_info=True)
        raise self.retry(exc=exc, countdown=60)