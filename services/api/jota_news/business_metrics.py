"""
Business metrics collection for JOTA News System.
"""
import logging
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Count, Q
from prometheus_client import Counter, Histogram, Gauge, Info
from apps.news.models import News, Category, Tag
from apps.webhooks.models import WebhookLog
from apps.notifications.models import Notification
from apps.classification.models import ClassificationResult
from apps.authentication.models import User, APIKey

logger = logging.getLogger(__name__)

# Business metrics
NEWS_ARTICLES_TOTAL = Counter(
    'jota_news_articles_total',
    'Total number of news articles',
    ['category', 'source', 'status']
)

NEWS_PROCESSING_TIME = Histogram(
    'jota_news_processing_seconds',
    'Time spent processing news articles',
    buckets=[0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0, 300.0, float('inf')]
)

WEBHOOK_EVENTS_TOTAL = Counter(
    'jota_webhooks_events_total',
    'Total number of webhook events',
    ['event_type', 'status']
)

WEBHOOK_RESPONSE_TIME = Histogram(
    'jota_webhooks_response_seconds',
    'Webhook response time',
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, float('inf')]
)

NOTIFICATIONS_SENT = Counter(
    'jota_notifications_sent_total',
    'Total notifications sent',
    ['channel', 'status']
)

CLASSIFICATION_ACCURACY = Gauge(
    'jota_classification_accuracy',
    'Classification accuracy percentage',
    ['model_type']
)

ACTIVE_USERS = Gauge(
    'jota_active_users',
    'Number of active users',
    ['user_type']
)

API_REQUESTS_TOTAL = Counter(
    'jota_api_requests_total',
    'Total API requests',
    ['method', 'endpoint', 'status']
)

USER_REGISTRATIONS = Counter(
    'jota_user_registrations_total',
    'Total user registrations',
    ['user_type']
)

NEWS_CATEGORIES = Gauge(
    'jota_news_categories_total',
    'Number of news categories'
)

NEWS_TAGS = Gauge(
    'jota_news_tags_total',
    'Number of news tags'
)

DATA_PIPELINE_STATUS = Gauge(
    'jota_data_pipeline_status',
    'Status of data pipeline components',
    ['component', 'status']
)


class BusinessMetricsCollector:
    """Collector for business metrics."""
    
    def __init__(self):
        self.last_update = timezone.now()
    
    def collect_news_metrics(self):
        """Collect news-related metrics."""
        try:
            # Count news by category
            for category in Category.objects.all():
                count = News.objects.filter(category=category).count()
                NEWS_ARTICLES_TOTAL.labels(
                    category=category.name,
                    source='api',
                    status='published'
                ).inc(count)
            
            # Count total categories and tags
            NEWS_CATEGORIES.set(Category.objects.count())
            NEWS_TAGS.set(Tag.objects.count())
            
            # Recent news processing
            recent_news = News.objects.filter(
                created_at__gte=timezone.now() - timedelta(hours=24)
            ).count()
            
            logger.info(f"Collected metrics for {recent_news} recent news articles")
            
        except Exception as e:
            logger.error(f"Error collecting news metrics: {e}")
    
    def collect_webhook_metrics(self):
        """Collect webhook-related metrics."""
        try:
            # Count webhook events by method and status
            webhook_stats = WebhookLog.objects.values(
                'method', 'status'
            ).annotate(count=Count('id'))
            
            for stat in webhook_stats:
                WEBHOOK_EVENTS_TOTAL.labels(
                    event_type=stat['method'],
                    status=stat['status']
                ).inc(stat['count'])
            
            # Calculate average response time for recent webhooks
            recent_webhooks = WebhookLog.objects.filter(
                created_at__gte=timezone.now() - timedelta(hours=1),
                processing_time__isnull=False
            )
            
            if recent_webhooks.exists():
                avg_response_time = sum(wh.processing_time for wh in recent_webhooks) / recent_webhooks.count()
                WEBHOOK_RESPONSE_TIME.observe(avg_response_time)
            
            logger.info(f"Collected webhook metrics for {recent_webhooks.count()} recent events")
            
        except Exception as e:
            logger.error(f"Error collecting webhook metrics: {e}")
    
    def collect_notification_metrics(self):
        """Collect notification-related metrics."""
        try:
            # Count notifications by channel and status
            notification_stats = Notification.objects.values(
                'channel', 'status'
            ).annotate(count=Count('id'))
            
            for stat in notification_stats:
                NOTIFICATIONS_SENT.labels(
                    channel=stat['channel'],
                    status=stat['status']
                ).inc(stat['count'])
            
            logger.info("Collected notification metrics")
            
        except Exception as e:
            logger.error(f"Error collecting notification metrics: {e}")
    
    def collect_classification_metrics(self):
        """Collect classification-related metrics."""
        try:
            # Get classification accuracy from recent results
            recent_results = ClassificationResult.objects.filter(
                created_at__gte=timezone.now() - timedelta(hours=24),
                is_accepted=True
            )
            
            if recent_results.exists():
                accuracy = sum(result.category_confidence for result in recent_results) / recent_results.count()
                CLASSIFICATION_ACCURACY.labels(model_type='news_classifier').set(accuracy)
            
            logger.info(f"Collected classification metrics for {recent_results.count()} recent results")
            
        except Exception as e:
            logger.error(f"Error collecting classification metrics: {e}")
    
    def collect_user_metrics(self):
        """Collect user-related metrics."""
        try:
            # Active users in the last 24 hours
            active_users = User.objects.filter(
                last_login__gte=timezone.now() - timedelta(hours=24)
            ).count()
            ACTIVE_USERS.labels(user_type='regular').set(active_users)
            
            # API key usage
            active_api_keys = APIKey.objects.filter(
                is_active=True,
                last_used__gte=timezone.now() - timedelta(hours=24)
            ).count()
            ACTIVE_USERS.labels(user_type='api').set(active_api_keys)
            
            # New registrations
            new_users = User.objects.filter(
                date_joined__gte=timezone.now() - timedelta(hours=24)
            ).count()
            USER_REGISTRATIONS.labels(user_type='regular').inc(new_users)
            
            logger.info(f"Collected user metrics: {active_users} active users, {new_users} new registrations")
            
        except Exception as e:
            logger.error(f"Error collecting user metrics: {e}")
    
    def collect_pipeline_status(self):
        """Collect data pipeline status metrics."""
        try:
            # Check various pipeline components
            components = {
                'news_ingestion': self._check_news_ingestion(),
                'classification_pipeline': self._check_classification_pipeline(),
                'webhook_processing': self._check_webhook_processing(),
                'notification_system': self._check_notification_system(),
            }
            
            for component, status in components.items():
                DATA_PIPELINE_STATUS.labels(
                    component=component,
                    status='healthy' if status else 'unhealthy'
                ).set(1 if status else 0)
            
            logger.info("Collected pipeline status metrics")
            
        except Exception as e:
            logger.error(f"Error collecting pipeline status: {e}")
    
    def _check_news_ingestion(self):
        """Check if news ingestion is working."""
        recent_news = News.objects.filter(
            created_at__gte=timezone.now() - timedelta(hours=1)
        ).exists()
        return recent_news
    
    def _check_classification_pipeline(self):
        """Check if classification pipeline is working."""
        recent_classifications = ClassificationResult.objects.filter(
            created_at__gte=timezone.now() - timedelta(hours=1)
        ).exists()
        return recent_classifications
    
    def _check_webhook_processing(self):
        """Check if webhook processing is working."""
        recent_webhooks = WebhookLog.objects.filter(
            created_at__gte=timezone.now() - timedelta(hours=1),
            status='success'
        ).exists()
        return recent_webhooks
    
    def _check_notification_system(self):
        """Check if notification system is working."""
        recent_notifications = Notification.objects.filter(
            created_at__gte=timezone.now() - timedelta(hours=1),
            status='sent'
        ).exists()
        return recent_notifications
    
    def collect_all_metrics(self):
        """Collect all business metrics."""
        logger.info("Starting business metrics collection")
        
        self.collect_news_metrics()
        self.collect_webhook_metrics()
        self.collect_notification_metrics()
        self.collect_classification_metrics()
        self.collect_user_metrics()
        self.collect_pipeline_status()
        
        self.last_update = timezone.now()
        logger.info("Business metrics collection completed")


# Global collector instance
business_metrics_collector = BusinessMetricsCollector()


def get_business_metrics():
    """Get current business metrics as a dictionary."""
    business_metrics_collector.collect_all_metrics()
    
    return {
        'news_articles_total': News.objects.count(),
        'categories_total': Category.objects.count(),
        'tags_total': Tag.objects.count(),
        'active_users': User.objects.filter(
            last_login__gte=timezone.now() - timedelta(hours=24)
        ).count(),
        'webhook_events_24h': WebhookLog.objects.filter(
            created_at__gte=timezone.now() - timedelta(hours=24)
        ).count(),
        'notifications_24h': Notification.objects.filter(
            created_at__gte=timezone.now() - timedelta(hours=24)
        ).count(),
        'last_update': business_metrics_collector.last_update.isoformat(),
    }