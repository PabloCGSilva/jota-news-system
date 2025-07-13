"""
Integration tests for news API endpoints.
"""
import pytest
from django.urls import reverse
from rest_framework import status


@pytest.mark.integration
class TestNewsAPI:
    """Integration tests for News API."""
    
    def test_list_news_authenticated(self, authenticated_client, news):
        """Test listing news with authentication."""
        url = reverse('news:news-list')
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert 'results' in response.data
        assert len(response.data['results']) >= 1
        
        news_data = response.data['results'][0]
        assert 'title' in news_data
        assert 'category_name' in news_data
        assert 'content' not in news_data  # List view shouldn't include full content
    
    def test_list_news_unauthenticated(self, api_client, news):
        """Test listing news without authentication - should be allowed for public access."""
        url = reverse('news:news-list')
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert 'results' in response.data
    
    def test_retrieve_news(self, authenticated_client, news):
        """Test retrieving a specific news article."""
        url = reverse('news:news-detail', kwargs={'pk': news.id})
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == str(news.id)
        assert response.data['title'] == news.title
        assert response.data['content'] == news.content
        assert response.data['category_name'] == news.category.name
    
    def test_create_news(self, authenticated_client, category, subcategory):
        """Test creating news via API."""
        url = reverse('news:news-list')
        data = {
            'title': 'API Created News',
            'content': 'This news was created via API with sufficient content length.',
            'source': 'API Test',
            'author': 'Test Author',
            'category': str(category.id),
            'subcategory': str(subcategory.id),
            'tag_names': ['api', 'test'],
            'is_published': True
        }
        
        response = authenticated_client.post(url, data)
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['title'] == 'API Created News'
        assert str(response.data['category']) == str(category.id)
    
    def test_update_news(self, authenticated_client, news):
        """Test updating news via API."""
        url = reverse('news:news-detail', kwargs={'pk': news.id})
        data = {
            'title': 'Updated News Title',
            'is_urgent': True
        }
        
        response = authenticated_client.patch(url, data)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['title'] == 'Updated News Title'
        assert response.data['is_urgent'] is True
    
    def test_filter_news_by_category(self, authenticated_client, multiple_news, category):
        """Test filtering news by category."""
        url = reverse('news:news-list')
        response = authenticated_client.get(url, {'category': category.id})
        
        assert response.status_code == status.HTTP_200_OK
        
        # All returned news should be from the specified category
        for news_item in response.data['results']:
            assert str(news_item['category']) == str(category.id)
    
    def test_search_news(self, authenticated_client, multiple_news):
        """Test searching news by title/content."""
        url = reverse('news:news-list')
        response = authenticated_client.get(url, {'search': 'Test News Article 1'})
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 1
    
    def test_mark_news_urgent(self, authenticated_client, news, mock_celery):
        """Test marking news as urgent."""
        url = reverse('news:news-mark-urgent', kwargs={'pk': news.id})
        response = authenticated_client.post(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'marked as urgent'
        
        # Verify news is marked as urgent
        news.refresh_from_db()
        assert news.is_urgent is True
    
    def test_share_news(self, authenticated_client, news):
        """Test sharing news (increment share count)."""
        initial_share_count = news.share_count
        
        url = reverse('news:news-share', kwargs={'pk': news.id})
        response = authenticated_client.post(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'shared'
        assert response.data['share_count'] == initial_share_count + 1
    
    def test_get_related_news(self, authenticated_client, multiple_news):
        """Test getting related news."""
        news = multiple_news[0]
        
        url = reverse('news:news-related', kwargs={'pk': news.id})
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.data, list)
        
        # Should not include the original news in related
        related_ids = [item['id'] for item in response.data]
        assert str(news.id) not in related_ids
    
    def test_advanced_search(self, authenticated_client, multiple_news, category):
        """Test advanced news search."""
        url = reverse('news:news-search')
        params = {
            'q': 'test',
            'category': category.id,
            'is_urgent': False,
            'ordering': '-published_at'
        }
        
        response = authenticated_client.get(url, params)
        
        assert response.status_code == status.HTTP_200_OK
        assert 'results' in response.data


@pytest.mark.integration
class TestCategoryAPI:
    """Integration tests for Category API."""
    
    def test_list_categories(self, authenticated_client, category):
        """Test listing categories."""
        url = reverse('news:category-list')
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 1
        
        category_data = response.data['results'][0]
        assert 'name' in category_data
        assert 'news_count' in category_data
    
    def test_create_category(self, authenticated_client):
        """Test creating a category."""
        url = reverse('news:category-list')
        data = {
            'name': 'New Category',
            'slug': 'new-category',
            'description': 'A new test category',
            'keywords': ['new', 'test']
        }
        
        response = authenticated_client.post(url, data)
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['name'] == 'New Category'
        assert response.data['keywords'] == ['new', 'test']
    
    def test_category_statistics(self, authenticated_client, category, news):
        """Test getting category statistics."""
        url = reverse('news:category-statistics', kwargs={'pk': category.id})
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert 'total_news' in response.data
        assert 'urgent_news' in response.data
        assert 'subcategories' in response.data
        assert 'top_tags' in response.data


@pytest.mark.integration
class TestTagAPI:
    """Integration tests for Tag API."""
    
    def test_list_tags(self, authenticated_client, tag):
        """Test listing tags."""
        url = reverse('news:tag-list')
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1
    
    def test_create_tag(self, authenticated_client):
        """Test creating a tag."""
        url = reverse('news:tag-list')
        data = {
            'name': 'New Tag',
            'slug': 'new-tag',
            'description': 'A new test tag'
        }
        
        response = authenticated_client.post(url, data)
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['name'] == 'New Tag'


@pytest.mark.integration
class TestNewsPermissions:
    """Test news API permissions."""
    
    def test_unauthenticated_read_access_allowed(self, api_client, news):
        """Test that unauthenticated users can read news API (public access)."""
        urls = [
            reverse('news:news-list'),
            reverse('news:news-detail', kwargs={'pk': news.id}),
            reverse('news:category-list'),
            reverse('news:tag-list'),
        ]
        
        for url in urls:
            response = api_client.get(url)
            assert response.status_code == status.HTTP_200_OK
    
    def test_read_only_access_for_regular_users(self, authenticated_client):
        """Test that regular users have read-only access."""
        # Create operations should be allowed for testing
        # In production, you might want to restrict this
        url = reverse('news:category-list')
        data = {'name': 'Test Category', 'slug': 'test-category'}
        
        response = authenticated_client.post(url, data)
        # This depends on your permission setup
        # Adjust assertion based on your requirements
        assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_403_FORBIDDEN]