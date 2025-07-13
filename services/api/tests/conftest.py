"""
Pytest configuration and fixtures.
"""
import pytest
import uuid
from datetime import datetime, timedelta
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.news.models import Category, Subcategory, Tag, News
from apps.webhooks.models import WebhookSource
from apps.classification.models import ClassificationRule
from apps.notifications.models import NotificationChannel, NotificationSubscription


@pytest.fixture
def api_client():
    """API client for making requests."""
    return APIClient()


@pytest.fixture
def user(db):
    """Create a test user."""
    User = get_user_model()
    user, created = User.objects.get_or_create(
        username='testuser',
        defaults={
            'email': 'test@example.com',
            'first_name': 'Test',
            'last_name': 'User'
        }
    )
    if created:
        user.set_password('testpass123')
        user.save()
    return user


@pytest.fixture
def admin_user(db):
    """Create an admin user."""
    User = get_user_model()
    user, created = User.objects.get_or_create(
        username='admin',
        defaults={
            'email': 'admin@example.com',
            'is_staff': True,
            'is_superuser': True
        }
    )
    if created:
        user.set_password('adminpass123')
        user.save()
    return user


@pytest.fixture
def authenticated_client(api_client, user):
    """API client with authenticated user."""
    refresh = RefreshToken.for_user(user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    api_client.user = user
    return api_client


@pytest.fixture
def admin_client(api_client, admin_user):
    """API client with authenticated admin user."""
    refresh = RefreshToken.for_user(admin_user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    api_client.user = admin_user
    return api_client


@pytest.fixture
def category(db):
    """Create a test category."""
    category, created = Category.objects.get_or_create(
        name='Test Category',
        defaults={
            'slug': 'test-category',
            'description': 'Test category description',
            'keywords': ['test', 'category', 'sample']
        }
    )
    return category


@pytest.fixture
def subcategory(db, category):
    """Create a test subcategory."""
    return Subcategory.objects.create(
        name='Test Subcategory',
        slug='test-subcategory',
        description='Test subcategory description',
        category=category,
        keywords=['subcategory', 'test']
    )


@pytest.fixture
def tag(db):
    """Create a test tag."""
    tag, created = Tag.objects.get_or_create(
        name='Test Tag',
        defaults={
            'slug': 'test-tag',
            'description': 'Test tag description'
        }
    )
    return tag


@pytest.fixture
def news(db, category, subcategory, tag):
    """Create a test news article."""
    news_item = News.objects.create(
        title='Test News Article',
        content='This is a test news article content with enough text to be meaningful.',
        summary='Test summary',
        source='Test Source',
        author='Test Author',
        category=category,
        subcategory=subcategory,
        published_at=timezone.now(),
        is_published=True,
        external_id=f'test-news-{uuid.uuid4().hex[:8]}'
    )
    news_item.tags.add(tag)
    return news_item


@pytest.fixture
def urgent_news(db, category):
    """Create an urgent news article."""
    return News.objects.create(
        title='URGENT: Breaking News',
        content='This is urgent breaking news that requires immediate attention.',
        source='Breaking News Source',
        category=category,
        is_urgent=True,
        is_published=True,
        published_at=timezone.now(),
        external_id=f'urgent-news-{uuid.uuid4().hex[:8]}'
    )


@pytest.fixture
def webhook_source(db):
    """Create a test webhook source."""
    return WebhookSource.objects.create(
        name='Test Webhook Source',
        description='Test webhook source for testing',
        endpoint_url='https://test.example.com/webhook',
        secret_key='test_secret_key',
        is_active=True,
        expected_content_type='application/json',
        requires_authentication=False,
        rate_limit_per_minute=100
    )


@pytest.fixture
def classification_rule(db, category):
    """Create a test classification rule."""
    return ClassificationRule.objects.create(
        name='Test Classification Rule',
        description='Test rule for classification',
        rule_type='keyword',
        target_category=category,
        keywords=['test', 'sample', 'demo'],
        weight=1.0,
        confidence_threshold=0.5,
        is_active=True,
        priority=100
    )


@pytest.fixture
def notification_channel(db):
    """Create a test notification channel."""
    return NotificationChannel.objects.create(
        name='Test WhatsApp Channel',
        channel_type='whatsapp',
        description='Test WhatsApp notification channel',
        config={
            'access_token': 'test_token',
            'phone_number_id': 'test_phone_id'
        },
        is_active=True,
        rate_limit_per_minute=60,
        rate_limit_per_hour=1000
    )


@pytest.fixture
def notification_subscription(db, user, notification_channel, category):
    """Create a test notification subscription."""
    subscription = NotificationSubscription.objects.create(
        user=user,
        channel=notification_channel,
        destination='+5511999999999',
        min_priority='medium',
        is_active=True
    )
    subscription.categories.add(category)
    return subscription


@pytest.fixture
def sample_webhook_data():
    """Sample webhook data for testing."""
    return {
        'title': 'Sample News from Webhook',
        'content': 'This is sample news content received via webhook. It contains enough text to be processed properly.',
        'source': 'Webhook Source',
        'author': 'Webhook Author',
        'published_at': timezone.now().isoformat(),
        'external_id': str(uuid.uuid4()),
        'category_hint': 'test category',
        'tags': ['webhook', 'test', 'sample'],
        'is_urgent': False,
        'metadata': {
            'webhook_version': '1.0',
            'source_system': 'test'
        }
    }


@pytest.fixture
def multiple_news(db, category, subcategory):
    """Create multiple news articles for bulk testing."""
    news_items = []
    
    for i in range(5):
        news_item = News.objects.create(
            title=f'Test News Article {i+1}',
            content=f'This is test news article number {i+1} with unique content.',
            source=f'Test Source {i+1}',
            author=f'Test Author {i+1}',
            category=category,
            subcategory=subcategory if i % 2 == 0 else None,
            published_at=timezone.now() - timedelta(days=i),
            is_published=True,
            is_urgent=i == 0,  # First one is urgent
            external_id=f'test-multiple-{i+1}-{uuid.uuid4().hex[:8]}'
        )
        news_items.append(news_item)
    
    return news_items


@pytest.fixture
def mock_whatsapp_api(monkeypatch):
    """Mock WhatsApp API responses."""
    def mock_post(url, json=None, headers=None, timeout=None):
        class MockResponse:
            status_code = 200
            
            def json(self):
                return {
                    'messages': [{'id': 'mock_message_id_123'}],
                    'meta': {'api_status': 'stable'}
                }
        
        return MockResponse()
    
    def mock_get(url, headers=None, timeout=None):
        class MockResponse:
            status_code = 200
            
            def json(self):
                return {
                    'id': 'mock_message_id_123',
                    'status': 'delivered',
                    'timestamp': timezone.now().timestamp()
                }
        
        return MockResponse()
    
    import requests
    monkeypatch.setattr(requests, 'post', mock_post)
    monkeypatch.setattr(requests, 'get', mock_get)


@pytest.fixture
def mock_classification(monkeypatch):
    """Mock classification functionality."""
    def mock_classify_news(title, content, method='hybrid'):
        return {
            'category': 'test category',
            'subcategory': 'test subcategory',
            'category_confidence': 0.85,
            'subcategory_confidence': 0.75,
            'is_urgent': 'urgent' in title.lower(),
            'urgency_confidence': 0.9 if 'urgent' in title.lower() else 0.1,
            'method': method,
            'processing_time': 0.05,
            'details': {
                'features': {'test': True},
                'keyword_matches': ['test']
            }
        }
    
    from apps.classification import classifier
    monkeypatch.setattr(classifier, 'classify_news', mock_classify_news)


@pytest.fixture
def mock_celery(monkeypatch):
    """Mock Celery tasks for testing."""
    def mock_delay(*args, **kwargs):
        class MockTask:
            id = 'mock_task_id'
            
            def get(self, timeout=None):
                return {'status': 'success'}
        
        return MockTask()
    
    # Mock common tasks
    from apps.classification import tasks as classification_tasks
    from apps.notifications import tasks as notification_tasks
    from apps.webhooks import tasks as webhook_tasks
    
    monkeypatch.setattr(classification_tasks.classify_news, 'delay', mock_delay)
    monkeypatch.setattr(notification_tasks.send_notification_task, 'delay', mock_delay)
    monkeypatch.setattr(webhook_tasks.process_webhook_async, 'delay', mock_delay)


# Mark fixtures for different test types
pytestmark = pytest.mark.django_db