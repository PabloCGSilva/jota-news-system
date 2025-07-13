"""
Authentication backends for JOTA News System.
"""
from django.contrib.auth.backends import BaseBackend
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import APIKey

User = get_user_model()


class APIKeyAuthentication(BaseBackend):
    """
    API Key authentication backend.
    
    Authenticates users using API keys in the Authorization header.
    Expected format: Authorization: Api-Key <api_key>
    """
    
    def authenticate(self, request, api_key=None, **kwargs):
        """
        Authenticate using API key.
        
        Args:
            request: HttpRequest object
            api_key: API key string from header
            
        Returns:
            User object if authenticated, None otherwise
        """
        if not api_key:
            return None
            
        try:
            # Find active API key
            api_key_obj = APIKey.objects.select_related('user').get(
                key=api_key,
                is_active=True
            )
            
            # Check if key is expired
            if api_key_obj.expires_at and api_key_obj.expires_at < timezone.now():
                return None
                
            # Update usage statistics
            api_key_obj.last_used = timezone.now()
            api_key_obj.usage_count += 1
            api_key_obj.save(update_fields=['last_used', 'usage_count'])
            
            # Return the user
            return api_key_obj.user
            
        except APIKey.DoesNotExist:
            return None
    
    def get_user(self, user_id):
        """
        Get user by ID.
        
        Args:
            user_id: User ID
            
        Returns:
            User object if found, None otherwise
        """
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None