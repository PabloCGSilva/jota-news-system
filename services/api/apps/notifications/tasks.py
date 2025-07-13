"""
Celery tasks for notifications.
"""
import logging
from celery import shared_task
from django.utils import timezone
from django.db.models import Count, Avg, Sum
from django.db import transaction
from datetime import timedelta

from .models import (
    NotificationChannel, NotificationSubscription, NotificationTemplate,
    Notification, NotificationStatistic
)
from .providers import send_notification, check_delivery_status

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def send_urgent_notification(self, news_id):
    """
    Send urgent news notification to all subscribers.
    """
    try:
        from apps.news.models import News
        
        news = News.objects.get(id=news_id)
        
        if not news.is_urgent:
            return {'status': 'not_urgent', 'news_id': str(news_id)}
        
        # Get all active subscriptions for urgent notifications
        subscriptions = NotificationSubscription.objects.filter(
            is_active=True,
            channel__is_active=True
        ).filter(
            models.Q(urgent_only=True) | 
            models.Q(min_priority__in=['urgent', 'high'])
        ).select_related('channel', 'user')
        
        # Filter by categories if specified
        category_filtered_subs = []
        for sub in subscriptions:
            if sub.categories.exists():
                if news.category in sub.categories.all():
                    category_filtered_subs.append(sub)
            else:
                category_filtered_subs.append(sub)
        
        # Filter by keywords if specified
        keyword_filtered_subs = []
        for sub in category_filtered_subs:
            if sub.keywords:
                text_to_search = f"{news.title} {news.content}".lower()
                if any(keyword.lower() in text_to_search for keyword in sub.keywords):
                    keyword_filtered_subs.append(sub)
            else:
                keyword_filtered_subs.append(sub)
        
        notifications_created = 0
        
        for subscription in keyword_filtered_subs:
            # Check quiet hours
            now = timezone.now().time()
            if (subscription.quiet_hours_start and subscription.quiet_hours_end and
                subscription.quiet_hours_start <= now <= subscription.quiet_hours_end):
                continue
            
            # Get template
            template = NotificationTemplate.objects.filter(
                channel=subscription.channel,
                template_type='urgent_news',
                is_active=True
            ).first()
            
            if not template:
                template = NotificationTemplate.objects.filter(
                    channel=subscription.channel,
                    template_type='urgent_news',
                    is_default=True
                ).first()
            
            # Prepare context
            context = {
                'title': news.title,
                'content': news.content[:300] + '...' if len(news.content) > 300 else news.content,
                'summary': news.summary,
                'source': news.source,
                'author': news.author,
                'category': news.category.name,
                'url': f"/news/{news.id}/",  # Adjust based on your URL structure
                'user_name': subscription.user.get_full_name() or subscription.user.username
            }
            
            # Render template
            if template:
                subject, message = template.render(context)
                template.increment_usage()
            else:
                subject = f"🚨 URGENTE: {news.title}"
                message = f"*{news.title}*\n\n{context['content']}\n\nFonte: {news.source}"
            
            # Create notification
            notification = Notification.objects.create(
                subscription=subscription,
                news=news,
                template=template,
                subject=subject,
                message=message,
                priority='urgent',
                metadata={
                    'news_id': str(news.id),
                    'category': news.category.name,
                    'is_urgent': True
                }
            )
            
            # Send immediately
            send_notification_task.delay(notification.id)
            notifications_created += 1
        
        logger.info(f"Created {notifications_created} urgent notifications for news {news_id}")
        
        return {
            'status': 'success',
            'news_id': str(news_id),
            'notifications_created': notifications_created
        }
        
    except Exception as exc:
        logger.error(f"Error sending urgent notification for news {news_id}: {str(exc)}", exc_info=True)
        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=5)
def send_notification_task(self, notification_id):
    """
    Send individual notification.
    """
    try:
        notification = Notification.objects.select_related(
            'subscription__channel',
            'subscription__user'
        ).get(id=notification_id)
        
        # Check if notification can be sent now
        if not notification.can_send_now():
            # Reschedule for later
            notification.scheduled_for = timezone.now() + timedelta(hours=1)
            notification.save()
            send_notification_task.apply_async(args=[notification_id], eta=notification.scheduled_for)
            return {'status': 'rescheduled', 'notification_id': str(notification_id)}
        
        # Update status
        notification.status = 'sending'
        notification.save()
        
        # Send notification
        success, external_id, response_data = send_notification(
            channel_type=notification.subscription.channel.channel_type,
            config=notification.subscription.channel.config,
            destination=notification.subscription.destination,
            subject=notification.subject,
            message=notification.message,
            metadata=notification.metadata
        )
        
        if success:
            notification.mark_sent(external_id, response_data)
            
            # Schedule delivery status check
            check_delivery_status_task.apply_async(
                args=[notification_id],
                countdown=300  # Check after 5 minutes
            )
            
            logger.info(f"Notification sent successfully: {notification_id}")
            
            return {
                'status': 'sent',
                'notification_id': str(notification_id),
                'external_id': external_id
            }
        else:
            error_message = response_data.get('error', 'Unknown error')
            notification.mark_failed(error_message)
            
            logger.error(f"Notification send failed: {notification_id} - {error_message}")
            
            return {
                'status': 'failed',
                'notification_id': str(notification_id),
                'error': error_message
            }
            
    except Notification.DoesNotExist:
        logger.error(f"Notification not found: {notification_id}")
        return {'status': 'not_found', 'notification_id': str(notification_id)}
    except Exception as exc:
        logger.error(f"Error sending notification {notification_id}: {str(exc)}", exc_info=True)
        
        # Mark as failed if max retries exceeded
        if self.request.retries >= self.max_retries:
            try:
                notification = Notification.objects.get(id=notification_id)
                notification.mark_failed(str(exc), retry=False)
            except:
                pass
        
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@shared_task(bind=True, max_retries=3)
def check_delivery_status_task(self, notification_id):
    """
    Check delivery status of a notification.
    """
    try:
        notification = Notification.objects.select_related(
            'subscription__channel'
        ).get(id=notification_id)
        
        if notification.status not in ['sent']:
            return {'status': 'skipped', 'notification_id': str(notification_id)}
        
        if not notification.external_id:
            return {'status': 'no_external_id', 'notification_id': str(notification_id)}
        
        # Check delivery status
        status, response_data = check_delivery_status(
            channel_type=notification.subscription.channel.channel_type,
            config=notification.subscription.channel.config,
            external_id=notification.external_id
        )
        
        if status == 'delivered':
            notification.mark_delivered(response_data)
        elif status == 'failed':
            notification.mark_failed(response_data.get('error', 'Delivery failed'), retry=False)
        
        return {
            'status': 'checked',
            'notification_id': str(notification_id),
            'delivery_status': status
        }
        
    except Notification.DoesNotExist:
        logger.error(f"Notification not found for status check: {notification_id}")
        return {'status': 'not_found', 'notification_id': str(notification_id)}
    except Exception as exc:
        logger.error(f"Error checking delivery status {notification_id}: {str(exc)}", exc_info=True)
        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3)
def send_daily_summary(self):
    """
    Send daily news summary to subscribers.
    """
    try:
        from apps.news.models import News
        
        today = timezone.now().date()
        yesterday = today - timedelta(days=1)
        
        # Get yesterday's news
        yesterday_news = News.objects.filter(
            published_at__date=yesterday,
            is_published=True
        ).order_by('-published_at')
        
        if not yesterday_news.exists():
            return {'status': 'no_news', 'date': str(yesterday)}
        
        # Get subscribers for daily summary
        subscriptions = NotificationSubscription.objects.filter(
            is_active=True,
            channel__is_active=True,
            min_priority__in=['low', 'medium', 'high', 'urgent']
        ).exclude(urgent_only=True).select_related('channel', 'user')
        
        notifications_created = 0
        
        for subscription in subscriptions:
            # Filter news by user's categories
            user_news = yesterday_news
            if subscription.categories.exists():
                user_news = user_news.filter(category__in=subscription.categories.all())
            
            if not user_news.exists():
                continue
            
            # Get template
            template = NotificationTemplate.objects.filter(
                channel=subscription.channel,
                template_type='daily_summary',
                is_active=True
            ).first()
            
            # Prepare context
            total_news = user_news.count()
            urgent_news = user_news.filter(is_urgent=True).count()
            categories = user_news.values('category__name').annotate(
                count=Count('id')
            ).order_by('-count')
            
            context = {
                'date': yesterday.strftime('%d/%m/%Y'),
                'total_news': total_news,
                'urgent_news': urgent_news,
                'categories': ', '.join([f"{cat['category__name']} ({cat['count']})" for cat in categories[:5]]),
                'top_news': '\n'.join([f"• {news.title}" for news in user_news[:5]]),
                'user_name': subscription.user.get_full_name() or subscription.user.username
            }
            
            # Render template
            if template:
                subject, message = template.render(context)
                template.increment_usage()
            else:
                subject = f"Resumo Diário JOTA - {context['date']}"
                message = f"Olá {context['user_name']},\n\nResumo de ontem ({context['date']}):\n\n📰 {total_news} notícias\n🚨 {urgent_news} urgentes\n\nPrincipais notícias:\n{context['top_news']}"
            
            # Create notification
            notification = Notification.objects.create(
                subscription=subscription,
                template=template,
                subject=subject,
                message=message,
                priority='low',
                metadata={
                    'type': 'daily_summary',
                    'date': str(yesterday),
                    'news_count': total_news
                }
            )
            
            # Send notification
            send_notification_task.delay(notification.id)
            notifications_created += 1
        
        logger.info(f"Created {notifications_created} daily summary notifications")
        
        return {
            'status': 'success',
            'date': str(yesterday),
            'notifications_created': notifications_created
        }
        
    except Exception as exc:
        logger.error(f"Error sending daily summary: {str(exc)}", exc_info=True)
        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3)
def process_pending_notifications(self):
    """
    Process pending notifications that are ready to be sent.
    """
    try:
        # Get pending notifications that are scheduled for now or earlier
        pending_notifications = Notification.objects.filter(
            status='pending',
            scheduled_for__lte=timezone.now()
        ).order_by('priority', 'scheduled_for')
        
        processed_count = 0
        
        for notification in pending_notifications[:100]:  # Process in batches
            send_notification_task.delay(notification.id)
            processed_count += 1
        
        logger.info(f"Queued {processed_count} pending notifications for processing")
        
        return {
            'status': 'success',
            'processed_count': processed_count
        }
        
    except Exception as exc:
        logger.error(f"Error processing pending notifications: {str(exc)}", exc_info=True)
        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3)
def update_notification_statistics(self):
    """
    Update daily notification statistics.
    """
    try:
        today = timezone.now().date()
        
        # Get all notification channels
        channels = NotificationChannel.objects.all()
        
        for channel in channels:
            # Get notifications for today
            today_notifications = Notification.objects.filter(
                subscription__channel=channel,
                created_at__date=today
            )
            
            # Calculate statistics
            total_sent = today_notifications.filter(status__in=['sent', 'delivered']).count()
            total_delivered = today_notifications.filter(status='delivered').count()
            total_failed = today_notifications.filter(status='failed').count()
            total_cancelled = today_notifications.filter(status='cancelled').count()
            
            # Priority breakdown
            urgent_notifications = today_notifications.filter(priority='urgent').count()
            high_notifications = today_notifications.filter(priority='high').count()
            medium_notifications = today_notifications.filter(priority='medium').count()
            low_notifications = today_notifications.filter(priority='low').count()
            
            # Calculate average delivery time
            delivered_notifications = today_notifications.filter(
                status='delivered',
                sent_at__isnull=False,
                delivered_at__isnull=False
            )
            
            avg_delivery_time = 0.0
            if delivered_notifications.exists():
                delivery_times = []
                for notif in delivered_notifications:
                    delivery_time = (notif.delivered_at - notif.sent_at).total_seconds()
                    delivery_times.append(delivery_time)
                avg_delivery_time = sum(delivery_times) / len(delivery_times)
            
            # Calculate delivery rate
            delivery_rate = (total_delivered / max(total_sent, 1)) * 100
            
            # Update or create statistics
            statistic, created = NotificationStatistic.objects.update_or_create(
                date=today,
                channel=channel,
                defaults={
                    'total_sent': total_sent,
                    'total_delivered': total_delivered,
                    'total_failed': total_failed,
                    'total_cancelled': total_cancelled,
                    'urgent_notifications': urgent_notifications,
                    'high_notifications': high_notifications,
                    'medium_notifications': medium_notifications,
                    'low_notifications': low_notifications,
                    'avg_delivery_time': avg_delivery_time,
                    'delivery_rate': delivery_rate,
                }
            )
            
            action = 'created' if created else 'updated'
            logger.info(f"Notification statistics {action} for {channel.name} on {today}")
        
        return {
            'status': 'success',
            'date': str(today),
            'channels_updated': channels.count()
        }
        
    except Exception as exc:
        logger.error(f"Error updating notification statistics: {str(exc)}", exc_info=True)
        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3)
def cleanup_old_notifications(self, days=30):
    """
    Clean up old notifications.
    """
    try:
        cutoff_date = timezone.now() - timedelta(days=days)
        
        # Delete old notifications
        deleted_count = Notification.objects.filter(
            created_at__lt=cutoff_date,
            status__in=['delivered', 'failed', 'cancelled']
        ).delete()[0]
        
        logger.info(f"Cleaned up {deleted_count} old notifications")
        
        return {
            'status': 'success',
            'deleted_count': deleted_count
        }
        
    except Exception as exc:
        logger.error(f"Error cleaning up notifications: {str(exc)}", exc_info=True)
        raise self.retry(exc=exc, countdown=60)