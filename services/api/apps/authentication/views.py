"""
Authentication views for JOTA News System.
"""
from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import logout
from drf_spectacular.utils import extend_schema, OpenApiResponse

from .models import User, APIKey
from .serializers import (
    UserSerializer, UserRegistrationSerializer, UserUpdateSerializer,
    PasswordChangeSerializer, CustomTokenObtainPairSerializer,
    APIKeySerializer, APIKeyCreateSerializer
)


class CustomTokenObtainPairView(TokenObtainPairView):
    """Custom JWT token obtain view."""
    serializer_class = CustomTokenObtainPairSerializer


class UserRegistrationView(generics.CreateAPIView):
    """User registration view."""
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]
    
    @extend_schema(
        summary="Register a new user",
        description="Create a new user account with email and password",
        responses={
            201: OpenApiResponse(description="User created successfully"),
            400: OpenApiResponse(description="Validation error")
        }
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class UserProfileView(generics.RetrieveUpdateAPIView):
    """User profile view."""
    serializer_class = UserUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        return self.request.user
    
    @extend_schema(
        summary="Get user profile",
        description="Retrieve the authenticated user's profile information"
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
    
    @extend_schema(
        summary="Update user profile",
        description="Update the authenticated user's profile information"
    )
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)
    
    @extend_schema(
        summary="Partially update user profile",
        description="Partially update the authenticated user's profile information"
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)


class PasswordChangeView(generics.GenericAPIView):
    """Password change view."""
    serializer_class = PasswordChangeSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    @extend_schema(
        summary="Change password",
        description="Change the authenticated user's password",
        responses={
            200: OpenApiResponse(description="Password changed successfully"),
            400: OpenApiResponse(description="Validation error")
        }
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response({
            'message': 'Password changed successfully'
        }, status=status.HTTP_200_OK)


@extend_schema(
    summary="Logout user",
    description="Logout the authenticated user and blacklist refresh token",
    responses={
        200: OpenApiResponse(description="Logged out successfully"),
        400: OpenApiResponse(description="Invalid token")
    }
)
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def logout_view(request):
    """Logout view."""
    try:
        refresh_token = request.data.get('refresh_token')
        if refresh_token:
            token = RefreshToken(refresh_token)
            token.blacklist()
        
        logout(request)
        
        return Response({
            'message': 'Logged out successfully'
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({
            'error': 'Invalid token'
        }, status=status.HTTP_400_BAD_REQUEST)


class APIKeyListCreateView(generics.ListCreateAPIView):
    """API key list and create view."""
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return APIKey.objects.filter(user=self.request.user)
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return APIKeyCreateSerializer
        return APIKeySerializer
    
    @extend_schema(
        summary="List API keys",
        description="List all API keys for the authenticated user"
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
    
    @extend_schema(
        summary="Create API key",
        description="Create a new API key for the authenticated user"
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class APIKeyDetailView(generics.RetrieveUpdateDestroyAPIView):
    """API key detail view."""
    serializer_class = APIKeySerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return APIKey.objects.filter(user=self.request.user)
    
    @extend_schema(
        summary="Get API key details",
        description="Retrieve details of a specific API key"
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
    
    @extend_schema(
        summary="Update API key",
        description="Update a specific API key"
    )
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)
    
    @extend_schema(
        summary="Partially update API key",
        description="Partially update a specific API key"
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)
    
    @extend_schema(
        summary="Delete API key",
        description="Delete a specific API key"
    )
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)


@extend_schema(
    summary="Get current user",
    description="Get the authenticated user's information",
    responses={
        200: UserSerializer,
        401: OpenApiResponse(description="Authentication required")
    }
)
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def current_user_view(request):
    """Get current user view."""
    serializer = UserSerializer(request.user)
    return Response(serializer.data, status=status.HTTP_200_OK)


@extend_schema(
    summary="Refresh token",
    description="Refresh JWT access token using refresh token"
)
@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def refresh_token_view(request):
    """Refresh token view."""
    try:
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return Response({
                'error': 'Refresh token is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        token = RefreshToken(refresh_token)
        access_token = token.access_token
        
        return Response({
            'access': str(access_token),
            'refresh': str(token)
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({
            'error': 'Invalid refresh token'
        }, status=status.HTTP_400_BAD_REQUEST)