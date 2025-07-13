"""
Simple test to verify Django configuration is working.
"""
import pytest
from django.contrib.auth import get_user_model
from apps.news.models import Category


@pytest.mark.django_db
def test_django_setup():
    """Test that Django is properly configured."""
    User = get_user_model()
    
    # Create a user
    user = User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123'
    )
    
    assert user.username == 'testuser'
    assert user.email == 'test@example.com'
    assert user.check_password('testpass123')


@pytest.mark.django_db
def test_category_model():
    """Test Category model creation."""
    category = Category.objects.create(
        name='Test Category',
        slug='test-category',
        description='Test description',
        keywords=['test', 'category'],
        is_active=True
    )
    
    assert category.name == 'Test Category'
    assert category.slug == 'test-category'
    assert category.is_active is True
    assert 'test' in category.keywords


@pytest.mark.django_db
def test_database_connection():
    """Test that database connection works."""
    User = get_user_model()
    
    # Count should work without error
    initial_count = User.objects.count()
    assert initial_count >= 0
    
    # Create and verify
    User.objects.create_user(
        username='dbtest',
        email='dbtest@example.com',
        password='password123'
    )
    
    new_count = User.objects.count()
    assert new_count == initial_count + 1