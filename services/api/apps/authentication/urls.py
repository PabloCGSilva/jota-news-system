"""
Authentication URLs.
"""
from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView
)
from drf_spectacular.utils import extend_schema
from drf_spectacular.openapi import OpenApiTypes

from .views import (
    CustomTokenObtainPairView, UserRegistrationView, UserProfileView,
    PasswordChangeView, logout_view, APIKeyListCreateView, APIKeyDetailView,
    current_user_view, refresh_token_view
)

app_name = 'auth'

# Enhanced JWT views with OpenAPI documentation
class DocumentedTokenObtainPairView(CustomTokenObtainPairView):
    @extend_schema(
        summary="Obtain JWT token pair",
        description="""
        Obtain access and refresh JWT tokens by providing valid credentials.
        
        The access token should be included in the Authorization header for authenticated requests:
        `Authorization: Bearer <access_token>`
        
        Access tokens expire in 60 minutes. Use the refresh token to obtain new access tokens.
        """,
        tags=['Authentication'],
        responses={
            200: {
                'description': 'Token obtained successfully',
                'content': {
                    'application/json': {
                        'example': {
                            'access': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...',
                            'refresh': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...'
                        }
                    }
                }
            },
            401: {
                'description': 'Invalid credentials',
                'content': {
                    'application/json': {
                        'example': {
                            'detail': 'No active account found with the given credentials'
                        }
                    }
                }
            }
        },
        request={
            'application/json': {
                'example': {
                    'username': 'your_username',
                    'password': 'your_password'
                }
            }
        }
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class DocumentedTokenRefreshView(TokenRefreshView):
    @extend_schema(
        summary="Refresh JWT access token",
        description="""
        Obtain a new access token using a valid refresh token.
        
        Refresh tokens are long-lived and should be stored securely.
        Use this endpoint when your access token expires.
        """,
        tags=['Authentication'],
        responses={
            200: {
                'description': 'Token refreshed successfully',
                'content': {
                    'application/json': {
                        'example': {
                            'access': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...'
                        }
                    }
                }
            },
            401: {
                'description': 'Invalid refresh token',
                'content': {
                    'application/json': {
                        'example': {
                            'detail': 'Token is invalid or expired',
                            'code': 'token_not_valid'
                        }
                    }
                }
            }
        },
        request={
            'application/json': {
                'example': {
                    'refresh': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...'
                }
            }
        }
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class DocumentedTokenVerifyView(TokenVerifyView):
    @extend_schema(
        summary="Verify JWT token",
        description="""
        Verify that a JWT token is valid and not expired.
        
        This endpoint can be used to check token validity before making API calls.
        """,
        tags=['Authentication'],
        responses={
            200: {
                'description': 'Token is valid',
                'content': {
                    'application/json': {
                        'example': {}
                    }
                }
            },
            401: {
                'description': 'Token is invalid',
                'content': {
                    'application/json': {
                        'example': {
                            'detail': 'Token is invalid or expired',
                            'code': 'token_not_valid'
                        }
                    }
                }
            }
        },
        request={
            'application/json': {
                'example': {
                    'token': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...'
                }
            }
        }
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


urlpatterns = [
    # Token management
    path('token/', DocumentedTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', DocumentedTokenRefreshView.as_view(), name='token_refresh'),
    path('token/verify/', DocumentedTokenVerifyView.as_view(), name='token_verify'),
    path('logout/', logout_view, name='logout'),
    
    # User management
    path('register/', UserRegistrationView.as_view(), name='user_register'),
    path('profile/', UserProfileView.as_view(), name='user_profile'),
    path('current/', current_user_view, name='current_user'),
    path('password/change/', PasswordChangeView.as_view(), name='password_change'),
    
    # API Keys
    path('api-keys/', APIKeyListCreateView.as_view(), name='api_keys'),
    path('api-keys/<uuid:pk>/', APIKeyDetailView.as_view(), name='api_key_detail'),
]