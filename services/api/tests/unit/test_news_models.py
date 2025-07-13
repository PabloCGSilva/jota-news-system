"""
Unit tests for news models.
"""
import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.utils import timezone
from datetime import timedelta

from apps.news.models import Category, Subcategory, Tag, News, NewsProcessingLog


@pytest.mark.unit
class TestCategoryModel:
    """Tests for Category model."""
    
    def test_create_category(self, db):
        """Test creating a category."""
        import uuid
        unique_name = f'Test Technology {uuid.uuid4().hex[:8]}'
        unique_slug = f'test-technology-{uuid.uuid4().hex[:8]}'
        
        category = Category.objects.create(
            name=unique_name,
            slug=unique_slug,
            description='Technology news',
            keywords=['tech', 'innovation', 'digital']
        )
        
        assert category.name == unique_name
        assert category.slug == unique_slug
        assert category.is_active is True
        assert 'tech' in category.keywords
        assert str(category) == unique_name
    
    def test_category_unique_name(self, db, category):
        """Test category name uniqueness."""
        with pytest.raises(IntegrityError):
            Category.objects.create(
                name=category.name,
                slug='different-slug'
            )
    
    def test_category_unique_slug(self, db, category):
        """Test category slug uniqueness."""
        with pytest.raises(IntegrityError):
            Category.objects.create(
                name='Different Name',
                slug=category.slug
            )


@pytest.mark.unit
class TestSubcategoryModel:
    """Tests for Subcategory model."""
    
    def test_create_subcategory(self, db, category):
        """Test creating a subcategory."""
        subcategory = Subcategory.objects.create(
            name='AI & Machine Learning',
            slug='ai-ml',
            description='AI and ML news',
            category=category,
            keywords=['ai', 'ml', 'artificial intelligence']
        )
        
        assert subcategory.name == 'AI & Machine Learning'
        assert subcategory.category == category
        assert subcategory.is_active is True
        assert str(subcategory) == f"{category.name} - AI & Machine Learning"
    
    def test_subcategory_category_slug_unique_together(self, db, category):
        """Test subcategory category+slug uniqueness."""
        Subcategory.objects.create(
            name='Test Sub 1',
            slug='test-sub',
            category=category
        )
        
        with pytest.raises(IntegrityError):
            Subcategory.objects.create(
                name='Test Sub 2',
                slug='test-sub',
                category=category
            )


@pytest.mark.unit
class TestTagModel:
    """Tests for Tag model."""
    
    def test_create_tag(self, db):
        """Test creating a tag."""
        tag = Tag.objects.create(
            name='Python',
            slug='python',
            description='Python programming language'
        )
        
        assert tag.name == 'Python'
        assert tag.slug == 'python'
        assert tag.usage_count == 0
        assert str(tag) == 'Python'
    
    def test_tag_unique_name(self, db, tag):
        """Test tag name uniqueness."""
        with pytest.raises(IntegrityError):
            Tag.objects.create(
                name=tag.name,
                slug='different-slug'
            )


@pytest.mark.unit
class TestNewsModel:
    """Tests for News model."""
    
    def test_create_news(self, db, category, subcategory, tag):
        """Test creating a news article."""
        news = News.objects.create(
            title='Test News Article',
            content='This is a test news article with sufficient content.',
            summary='Test summary',
            source='Test Source',
            author='Test Author',
            category=category,
            subcategory=subcategory,
            published_at=timezone.now()
        )
        news.tags.add(tag)
        
        assert news.title == 'Test News Article'
        assert news.category == category
        assert news.subcategory == subcategory
        assert news.is_published is True
        assert news.is_urgent is False
        assert news.word_count > 0
        assert news.reading_time >= 1
        assert tag in news.tags.all()
        assert str(news) == 'Test News Article'
    
    def test_news_auto_word_count(self, db, category):
        """Test automatic word count calculation."""
        content = 'This is a test content with exactly ten words here.'
        news = News.objects.create(
            title='Test',
            content=content,
            source='Test',
            category=category
        )
        
        assert news.word_count == len(content.split())
    
    def test_news_auto_reading_time(self, db, category):
        """Test automatic reading time calculation."""
        # Create content with ~400 words (should be 2 minutes at 200 WPM)
        content = ' '.join(['word'] * 400)
        news = News.objects.create(
            title='Test',
            content=content,
            source='Test',
            category=category
        )
        
        assert news.reading_time == 2
    
    def test_news_auto_summary_generation(self, db, category):
        """Test automatic summary generation."""
        long_content = 'A' * 1000  # Content longer than 500 chars
        news = News.objects.create(
            title='Test',
            content=long_content,
            source='Test',
            category=category
        )
        
        assert news.summary == long_content[:497] + '...'
    
    def test_news_increment_view_count(self, db, news):
        """Test incrementing view count."""
        initial_count = news.view_count
        news.increment_view_count()
        
        assert news.view_count == initial_count + 1
    
    def test_news_increment_share_count(self, db, news):
        """Test incrementing share count."""
        initial_count = news.share_count
        news.increment_share_count()
        
        assert news.share_count == initial_count + 1
    
    def test_news_external_id_unique(self, db, category):
        """Test external ID uniqueness."""
        News.objects.create(
            title='Test 1',
            content='Content 1',
            source='Source 1',
            category=category,
            external_id='unique_id_123'
        )
        
        with pytest.raises(IntegrityError):
            News.objects.create(
                title='Test 2',
                content='Content 2',
                source='Source 2',
                category=category,
                external_id='unique_id_123'
            )


@pytest.mark.unit
class TestNewsProcessingLog:
    """Tests for NewsProcessingLog model."""
    
    def test_create_processing_log(self, db, news):
        """Test creating a processing log."""
        log = NewsProcessingLog.objects.create(
            news=news,
            stage='classification',
            status='success',
            message='Successfully classified news',
            processing_time=0.05
        )
        
        assert log.news == news
        assert log.stage == 'classification'
        assert log.status == 'success'
        assert log.processing_time == 0.05
        assert str(log) == f"{news.title} - classification - success"