"""
Unit tests for news serializers.
"""
import pytest
from django.utils import timezone
from rest_framework.test import APIRequestFactory

from apps.news.serializers import (
    CategorySerializer, SubcategorySerializer, TagSerializer,
    NewsListSerializer, NewsDetailSerializer, NewsCreateSerializer,
    NewsUpdateSerializer
)


@pytest.mark.unit
class TestCategorySerializer:
    """Tests for CategorySerializer."""
    
    def test_serialize_category(self, category):
        """Test serializing a category."""
        serializer = CategorySerializer(category)
        data = serializer.data
        
        assert data['name'] == category.name
        assert data['slug'] == category.slug
        assert data['description'] == category.description
        assert data['keywords'] == category.keywords
        assert data['is_active'] is True
        assert 'news_count' in data
        assert 'created_at' in data
    
    def test_deserialize_category(self, db):
        """Test deserializing category data."""
        data = {
            'name': 'New Category',
            'slug': 'new-category',
            'description': 'A new test category',
            'keywords': ['new', 'test'],
            'is_active': True
        }
        
        serializer = CategorySerializer(data=data)
        assert serializer.is_valid()
        
        category = serializer.save()
        assert category.name == 'New Category'
        assert category.keywords == ['new', 'test']


@pytest.mark.unit
class TestSubcategorySerializer:
    """Tests for SubcategorySerializer."""
    
    def test_serialize_subcategory(self, subcategory):
        """Test serializing a subcategory."""
        serializer = SubcategorySerializer(subcategory)
        data = serializer.data
        
        assert data['name'] == subcategory.name
        assert str(data['category']) == str(subcategory.category.id)
        assert data['category_name'] == subcategory.category.name
        assert 'news_count' in data


@pytest.mark.unit
class TestTagSerializer:
    """Tests for TagSerializer."""
    
    def test_serialize_tag(self, tag):
        """Test serializing a tag."""
        serializer = TagSerializer(tag)
        data = serializer.data
        
        assert data['name'] == tag.name
        assert data['slug'] == tag.slug
        assert data['usage_count'] == tag.usage_count


@pytest.mark.unit
class TestNewsSerializers:
    """Tests for News serializers."""
    
    def test_news_list_serializer(self, news):
        """Test NewsListSerializer."""
        serializer = NewsListSerializer(news)
        data = serializer.data
        
        assert data['title'] == news.title
        assert data['summary'] == news.summary
        assert data['category_name'] == news.category.name
        assert data['subcategory_name'] == news.subcategory.name
        assert len(data['tags']) > 0
        assert 'content' not in data  # Should not include full content
    
    def test_news_detail_serializer(self, news):
        """Test NewsDetailSerializer."""
        serializer = NewsDetailSerializer(news)
        data = serializer.data
        
        assert data['title'] == news.title
        assert data['content'] == news.content
        assert data['category_name'] == news.category.name
        assert data['word_count'] == news.word_count
        assert data['reading_time'] == news.reading_time
    
    def test_news_create_serializer(self, db, category, subcategory):
        """Test NewsCreateSerializer."""
        data = {
            'title': 'New News Article',
            'content': 'This is new news content with sufficient length.',
            'source': 'Test Source',
            'author': 'Test Author',
            'category': str(category.id),
            'subcategory': str(subcategory.id),
            'tag_names': ['tag1', 'tag2'],
            'is_urgent': False,
            'is_published': True
        }
        
        serializer = NewsCreateSerializer(data=data)
        assert serializer.is_valid(), serializer.errors
        
        news = serializer.save()
        assert news.title == 'New News Article'
        assert news.category == category
        assert news.subcategory == subcategory
        assert news.tags.count() == 2
    
    def test_news_update_serializer(self, news):
        """Test NewsUpdateSerializer."""
        data = {
            'title': 'Updated Title',
            'is_urgent': True,
            'tag_names': ['updated', 'tag']
        }
        
        serializer = NewsUpdateSerializer(news, data=data, partial=True)
        assert serializer.is_valid()
        
        updated_news = serializer.save()
        assert updated_news.title == 'Updated Title'
        assert updated_news.is_urgent is True
        assert updated_news.tags.filter(name='updated').exists()
    
    def test_news_create_serializer_validation(self, db):
        """Test NewsCreateSerializer validation."""
        # Missing required fields
        data = {
            'title': 'Test',
            # Missing content, source, category
        }
        
        serializer = NewsCreateSerializer(data=data)
        assert not serializer.is_valid()
        assert 'content' in serializer.errors
        assert 'source' in serializer.errors
        assert 'category' in serializer.errors
    
    def test_news_create_with_duplicate_external_id(self, db, category, news):
        """Test creating news with duplicate external_id."""
        data = {
            'title': 'Another News',
            'content': 'Different content',
            'source': 'Different Source',
            'category': str(category.id),
            'external_id': news.external_id  # Duplicate external_id
        }
        
        if news.external_id:  # Only test if original news has external_id
            serializer = NewsCreateSerializer(data=data)
            # Serializer should catch the duplicate external_id via UniqueValidator
            assert not serializer.is_valid()  # Should fail validation
            assert 'external_id' in serializer.errors