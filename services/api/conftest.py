"""
Pytest configuration and fixtures for JOTA News System tests.
"""
import os
import django
from django.conf import settings

# Configure Django settings before importing Django components
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'jota_news.settings')
django.setup()

# Now import Django components
import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from apps.news.models import Category, Subcategory, News, Tag
from apps.webhooks.models import WebhookSource
from apps.notifications.models import NotificationChannel, NotificationSubscription
from apps.authentication.models import APIKey
import uuid
from datetime import datetime, timedelta
from django.utils import timezone

User = get_user_model()


@pytest.fixture
def api_client():
    """API client for testing."""
    return APIClient()


@pytest.fixture
def user():
    """Create a test user."""
    User = get_user_model()
    return User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123',
        first_name='Test',
        last_name='User'
    )


@pytest.fixture
def admin_user():
    """Create an admin user."""
    return User.objects.create_superuser(
        username='admin',
        email='admin@example.com',
        password='adminpass123'
    )


@pytest.fixture
def authenticated_client(api_client, user):
    """API client with authenticated user."""
    refresh = RefreshToken.for_user(user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return api_client


@pytest.fixture
def admin_client(api_client, admin_user):
    """API client with admin user."""
    refresh = RefreshToken.for_user(admin_user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return api_client


@pytest.fixture
def category():
    """Create a test category."""
    return Category.objects.create(
        name='Politics',
        slug='politics',
        description='Political news and updates',
        keywords=['government', 'politics', 'election', 'congress'],
        is_active=True
    )


@pytest.fixture
def subcategory(category):
    """Create a test subcategory."""
    return Subcategory.objects.create(
        name='Federal Government',
        slug='federal-government',
        description='Federal government news',
        category=category,
        keywords=['federal', 'government', 'ministries'],
        is_active=True
    )


@pytest.fixture
def tag():
    """Create a test tag."""
    return Tag.objects.create(
        name='Breaking News',
        slug='breaking-news',
        description='Breaking news stories'
    )


@pytest.fixture
def news_article(category, subcategory, tag):
    """Create a test news article."""
    article = News.objects.create(
        title='Test News Article',
        content='This is a test news article with some content.',
        summary='Test article summary',
        source='Test Source',
        source_url='https://example.com/news/1',
        author='Test Author',
        category=category,
        subcategory=subcategory,
        is_urgent=False,
        is_published=True,
        published_at=timezone.now()
    )
    article.tags.add(tag)
    return article


@pytest.fixture
def webhook_source():
    """Create a test webhook source."""
    return WebhookSource.objects.create(
        name='Test Source',
        slug='test-source',
        description='Test webhook source',
        url='https://api.test.com/webhook',
        secret_key='test-secret-key',
        is_active=True,
        content_type='application/json'
    )


@pytest.fixture
def notification_channel():
    """Create a test notification channel."""
    return NotificationChannel.objects.create(
        name='Test Email Channel',
        channel_type='email',
        description='Test email notifications',
        config={
            'smtp_server': 'smtp.example.com',
            'smtp_port': 587,
            'username': 'test@example.com',
            'password': 'password'
        },
        is_active=True,
        is_default=True
    )


@pytest.fixture
def notification_subscription(user, notification_channel, category):
    """Create a test notification subscription."""
    subscription = NotificationSubscription.objects.create(
        user=user,
        channel=notification_channel,
        destination='user@example.com',
        min_priority='medium',
        is_active=True
    )
    subscription.categories.add(category)
    return subscription


@pytest.fixture
def api_key(user):
    """Create a test API key."""
    return APIKey.objects.create(
        user=user,
        name='Test API Key',
        key='test-api-key-123',
        is_active=True
    )


@pytest.fixture
def sample_news_data():
    """Sample news data for testing."""
    return {
        'title': 'Breaking: New Economic Policy Announced',
        'content': 'The government has announced a new economic policy that will impact various sectors...',
        'summary': 'Government announces new economic policy',
        'source': 'Economic Times',
        'source_url': 'https://economictimes.com/policy',
        'author': 'Economic Reporter',
        'is_urgent': True,
        'tags': ['economy', 'policy', 'government']
    }


@pytest.fixture
def sample_webhook_data():
    """Sample webhook data for testing."""
    return {
        'title': 'External News Article',
        'content': 'This is news from an external source via webhook.',
        'source': 'External API',
        'author': 'External Author',
        'published_at': datetime.now().isoformat(),
        'metadata': {
            'source_id': 'ext-123',
            'priority': 'high'
        }
    }


# Database fixtures
@pytest.fixture(scope='session')
def django_db_setup():
    """Setup test database."""
    pass


@pytest.fixture
def transactional_db(db):
    """Use transactional database for tests that need transactions."""
    pass


# Mock fixtures
@pytest.fixture
def mock_classification_response():
    """Mock classification response."""
    return {
        'category': 'politics',
        'subcategory': 'federal-government',
        'category_confidence': 0.85,
        'subcategory_confidence': 0.78,
        'is_urgent': False,
        'urgency_confidence': 0.15,
        'method': 'hybrid',
        'processing_time': 0.234,
        'details': {
            'keyword_result': {
                'category': 'politics',
                'subcategory': 'federal-government',
                'confidence': 0.8
            },
            'ml_result': {
                'category': 'politics',
                'subcategory': 'federal-government',
                'confidence': 0.9
            }
        }
    }


@pytest.fixture
def mock_notification_response():
    """Mock notification response."""
    return {
        'id': str(uuid.uuid4()),
        'status': 'sent',
        'external_id': 'msg-123',
        'sent_at': timezone.now().isoformat(),
        'response_data': {
            'message_id': 'msg-123',
            'status': 'accepted'
        }
    }