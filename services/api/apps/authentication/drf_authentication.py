"""
DRF Authentication classes for JOTA News System.
"""
from rest_framework import authentication, exceptions
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import APIKey

User = get_user_model()


class APIKeyAuthentication(authentication.BaseAuthentication):
    """
    API Key authentication for Django REST Framework.
    
    Clients should authenticate by passing the API key in the 
    "Authorization" HTTP header, prepended with the string "Api-Key ".
    
    For example:
        Authorization: Api-Key 401f7ac837da42b97f613d789819ff93537bee6a
    """
    
    keyword = 'Api-Key'
    
    def authenticate(self, request):
        """
        Authenticate the request and return a two-tuple of (user, token).
        """
        auth = authentication.get_authorization_header(request).split()
        
        if not auth or auth[0].lower() != self.keyword.lower().encode():
            return None
            
        if len(auth) == 1:
            msg = 'Invalid API key header. No credentials provided.'
            raise exceptions.AuthenticationFailed(msg)
        elif len(auth) > 2:
            msg = 'Invalid API key header. API key string should not contain spaces.'
            raise exceptions.AuthenticationFailed(msg)
            
        try:
            api_key = auth[1].decode('utf-8')
        except UnicodeError:
            msg = 'Invalid API key header. API key string should not contain invalid characters.'
            raise exceptions.AuthenticationFailed(msg)
            
        return self.authenticate_credentials(api_key)
    
    def authenticate_credentials(self, key):
        """
        Authenticate the API key.
        
        Args:
            key: API key string
            
        Returns:
            tuple: (user, api_key_obj) if successful
            
        Raises:
            AuthenticationFailed: If authentication fails
        """
        try:
            api_key_obj = APIKey.objects.select_related('user').get(
                key=key,
                is_active=True
            )
        except APIKey.DoesNotExist:
            raise exceptions.AuthenticationFailed('Invalid API key.')
            
        # Check if key is expired
        if api_key_obj.expires_at and api_key_obj.expires_at < timezone.now():
            raise exceptions.AuthenticationFailed('API key has expired.')
            
        # Check if user is active
        if not api_key_obj.user.is_active:
            raise exceptions.AuthenticationFailed('User inactive or deleted.')
            
        # Update usage statistics
        api_key_obj.last_used = timezone.now()
        api_key_obj.usage_count += 1
        api_key_obj.save(update_fields=['last_used', 'usage_count'])
        
        return (api_key_obj.user, api_key_obj)
    
    def authenticate_header(self, request):
        """
        Return a string to be used as the value of the `WWW-Authenticate`
        header in a `401 Unauthenticated` response, or `None` if the
        authentication scheme should return `403 Permission Denied` responses.
        """
        return self.keyword