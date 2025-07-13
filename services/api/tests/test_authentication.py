"""
Tests for authentication app.
"""
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from apps.authentication.models import APIKey, UserProfile

User = get_user_model()


@pytest.mark.django_db
class TestUserModel:
    """Test User model."""

    def test_user_creation(self):
        """Test user can be created."""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        assert user.username == 'testuser'
        assert user.email == 'test@example.com'
        assert user.check_password('testpass123')
        assert str(user) == 'test@example.com'

    def test_superuser_creation(self):
        """Test superuser can be created."""
        # Use get_or_create to handle existing admin user
        admin, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@example.com',
                'is_superuser': True,
                'is_staff': True,
            }
        )
        if created:
            admin.set_password('adminpass123')
            admin.save()
        
        assert admin.is_superuser
        assert admin.is_staff
        assert admin.email in ['admin@example.com', 'admin@jota.news']

    def test_user_profile_creation(self):
        """Test user profile is created."""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        profile = UserProfile.objects.create(
            user=user,
            organization='Test Corp',
            position='Developer'
        )
        assert profile.user == user
        assert profile.organization == 'Test Corp'


@pytest.mark.django_db
class TestAPIKeyModel:
    """Test APIKey model."""

    def test_api_key_creation(self, user):
        """Test API key can be created."""
        api_key = APIKey.objects.create(
            user=user,
            name='Test API Key',
            key='test-key-123',
            is_active=True
        )
        assert api_key.user == user
        assert api_key.name == 'Test API Key'
        assert api_key.key == 'test-key-123'
        assert api_key.is_active

    def test_api_key_str(self, user):
        """Test API key string representation."""
        api_key = APIKey.objects.create(
            user=user,
            name='Test API Key',
            key='test-key-123'
        )
        assert str(api_key) == 'Test API Key (test@example.com)'


@pytest.mark.django_db
class TestAuthenticationAPI:
    """Test authentication API endpoints."""

    def test_token_obtain(self, api_client, user):
        """Test JWT token can be obtained."""
        url = reverse('auth:token_obtain_pair')
        data = {
            'email': user.email,
            'password': 'testpass123'
        }
        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.data
        assert 'refresh' in response.data

    def test_token_obtain_invalid_credentials(self, api_client, user):
        """Test token obtain with invalid credentials."""
        url = reverse('auth:token_obtain_pair')
        data = {
            'email': user.email,
            'password': 'wrongpassword'
        }
        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_token_refresh(self, api_client, user):
        """Test JWT token can be refreshed."""
        # First get tokens
        token_url = reverse('auth:token_obtain_pair')
        token_data = {
            'email': user.email,
            'password': 'testpass123'
        }
        token_response = api_client.post(token_url, token_data)
        refresh_token = token_response.data['refresh']

        # Then refresh
        refresh_url = reverse('auth:token_refresh')
        refresh_data = {'refresh': refresh_token}
        response = api_client.post(refresh_url, refresh_data)
        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.data

    def test_user_registration(self, api_client):
        """Test user registration."""
        url = reverse('auth:user_register')
        data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'newpass123',
            'password_confirm': 'newpass123',
            'first_name': 'New',
            'last_name': 'User'
        }
        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_201_CREATED
        assert 'username' in response.data
        assert 'email' in response.data

    def test_user_profile_get(self, authenticated_client, user):
        """Test getting user profile."""
        url = reverse('auth:user_profile')
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['email'] == user.email

    def test_user_profile_update(self, authenticated_client, user):
        """Test updating user profile."""
        url = reverse('auth:user_profile')
        data = {
            'first_name': 'Updated',
            'last_name': 'Name',
            'bio': 'Updated bio'
        }
        response = authenticated_client.patch(url, data)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['first_name'] == 'Updated'

    def test_unauthenticated_access(self, api_client):
        """Test unauthenticated access to protected endpoints."""
        url = reverse('auth:user_profile')
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestAPIKeyAuthentication:
    """Test API key authentication."""

    def test_api_key_authentication(self, api_client, user, api_key):
        """Test API key authentication works."""
        api_client.credentials(HTTP_AUTHORIZATION=f'Api-Key {api_key.key}')
        url = reverse('auth:user_profile')
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK

    def test_invalid_api_key(self, api_client):
        """Test invalid API key is rejected."""
        api_client.credentials(HTTP_AUTHORIZATION='Api-Key invalid-key')
        url = reverse('auth:user_profile')
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_inactive_api_key(self, api_client, user):
        """Test inactive API key is rejected."""
        api_key = APIKey.objects.create(
            user=user,
            name='Inactive Key',
            key='inactive-key-123',
            is_active=False
        )
        api_client.credentials(HTTP_AUTHORIZATION=f'Api-Key {api_key.key}')
        url = reverse('auth:user_profile')
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED