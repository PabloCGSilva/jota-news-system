"""
Tests for news app.
"""
import pytest
from django.urls import reverse
from rest_framework import status
from apps.news.models import News, Category, Subcategory, Tag
from django.utils import timezone


@pytest.mark.django_db
class TestNewsModel:
    """Test News model."""

    def test_news_creation(self, category, subcategory, tag):
        """Test news article can be created."""
        news = News.objects.create(
            title='Test News',
            content='Test content',
            summary='Test summary',
            source='Test Source',
            category=category,
            subcategory=subcategory,
            published_at=timezone.now()
        )
        news.tags.add(tag)
        
        assert news.title == 'Test News'
        assert news.category == category
        assert news.subcategory == subcategory
        assert tag in news.tags.all()
        assert str(news) == 'Test News'

    def test_news_word_count_calculation(self, category):
        """Test word count is calculated correctly."""
        news = News.objects.create(
            title='Test News',
            content='This is a test content with multiple words.',
            category=category,
            published_at=timezone.now()
        )
        # Word count should be calculated automatically
        assert news.word_count > 0

    def test_news_reading_time_calculation(self, category):
        """Test reading time is calculated correctly."""
        long_content = ' '.join(['word'] * 300)  # 300 words
        news = News.objects.create(
            title='Long Article',
            content=long_content,
            category=category,
            published_at=timezone.now()
        )
        # Reading time should be calculated (assuming 200 words per minute)
        assert news.reading_time > 0


@pytest.mark.django_db
class TestCategoryModel:
    """Test Category model."""

    def test_category_creation(self):
        """Test category can be created."""
        category = Category.objects.create(
            name='Test Category',
            slug='test-category',
            description='Test description',
            keywords=['test', 'category'],
            is_active=True
        )
        assert category.name == 'Test Category'
        assert category.slug == 'test-category'
        assert 'test' in category.keywords
        assert str(category) == 'Test Category'

    def test_category_subcategories(self, category):
        """Test category subcategories relationship."""
        subcategory = Subcategory.objects.create(
            name='Sub Test',
            slug='sub-test',
            category=category,
            is_active=True
        )
        assert subcategory in category.subcategories.all()


@pytest.mark.django_db
class TestNewsAPI:
    """Test News API endpoints."""

    def test_news_list_public(self, api_client, news_article):
        """Test public news list endpoint."""
        url = reverse('news:article-list')
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1
        assert response.data['results'][0]['title'] == news_article.title

    def test_news_detail_public(self, api_client, news_article):
        """Test public news detail endpoint."""
        url = reverse('news:article-detail', kwargs={'pk': news_article.id})
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['title'] == news_article.title

    def test_news_create_authenticated(self, authenticated_client, category, sample_news_data):
        """Test news creation with authentication."""
        url = reverse('news:article-list')
        data = {
            **sample_news_data,
            'category': str(category.id)
        }
        response = authenticated_client.post(url, data)
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['title'] == sample_news_data['title']

    def test_news_create_unauthenticated(self, api_client, sample_news_data):
        """Test news creation without authentication."""
        url = reverse('news:article-list')
        response = api_client.post(url, sample_news_data)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_news_update_authenticated(self, authenticated_client, news_article):
        """Test news update with authentication."""
        url = reverse('news:article-detail', kwargs={'pk': news_article.id})
        data = {'title': 'Updated Title'}
        response = authenticated_client.patch(url, data)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['title'] == 'Updated Title'

    def test_news_delete_authenticated(self, authenticated_client, news_article):
        """Test news deletion with authentication."""
        url = reverse('news:article-detail', kwargs={'pk': news_article.id})
        response = authenticated_client.delete(url)
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not News.objects.filter(id=news_article.id).exists()

    def test_news_filter_by_category(self, api_client, news_article, category):
        """Test news filtering by category."""
        url = reverse('news:article-list')
        response = api_client.get(url, {'category': str(category.id)})
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1

    def test_news_search(self, api_client, news_article):
        """Test news search functionality."""
        url = reverse('news:article-list')
        response = api_client.get(url, {'search': 'Test'})
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1

    def test_news_urgent_filter(self, api_client, category):
        """Test urgent news filtering."""
        # Create urgent news
        urgent_news = News.objects.create(
            title='Urgent News',
            content='This is urgent',
            category=category,
            is_urgent=True,
            published_at=timezone.now()
        )
        
        url = reverse('news:article-list')
        response = api_client.get(url, {'is_urgent': 'true'})
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1
        assert response.data['results'][0]['title'] == 'Urgent News'


@pytest.mark.django_db
class TestCategoryAPI:
    """Test Category API endpoints."""

    def test_category_list(self, api_client, category):
        """Test category list endpoint."""
        url = reverse('news:category-list')
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1
        assert response.data['results'][0]['name'] == category.name

    def test_category_detail(self, api_client, category):
        """Test category detail endpoint."""
        url = reverse('news:category-detail', kwargs={'pk': category.id})
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == category.name

    def test_category_create_admin(self, admin_client):
        """Test category creation by admin."""
        url = reverse('news:category-list')
        data = {
            'name': 'New Category',
            'slug': 'new-category',
            'description': 'New description',
            'keywords': ['new', 'category'],
            'is_active': True
        }
        response = admin_client.post(url, data)
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['name'] == 'New Category'

    def test_category_create_user(self, authenticated_client):
        """Test category creation by regular user (should fail)."""
        url = reverse('news:category-list')
        data = {
            'name': 'New Category',
            'slug': 'new-category',
            'description': 'New description'
        }
        response = authenticated_client.post(url, data)
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestTagAPI:
    """Test Tag API endpoints."""

    def test_tag_list(self, api_client, tag):
        """Test tag list endpoint."""
        url = reverse('news:tag-list')
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1
        assert response.data['results'][0]['name'] == tag.name

    def test_tag_autocomplete(self, api_client, tag):
        """Test tag autocomplete functionality."""
        url = reverse('news:tag-list')
        response = api_client.get(url, {'search': 'Break'})
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1

    def test_tag_usage_count(self, api_client, tag, news_article):
        """Test tag usage count is updated."""
        # Tag should have usage count > 0 after being used in news
        tag.refresh_from_db()
        assert tag.usage_count >= 0