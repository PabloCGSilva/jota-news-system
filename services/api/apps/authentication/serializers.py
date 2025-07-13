"""
Authentication serializers for JOTA News System.
"""
from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import User, UserProfile, APIKey


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model."""
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'phone', 'bio', 'timezone', 'language', 'is_active',
            'date_joined', 'last_login', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'date_joined', 'last_login', 'created_at', 'updated_at']


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for UserProfile model."""
    
    class Meta:
        model = UserProfile
        fields = [
            'organization', 'position', 'department',
            'email_notifications', 'sms_notifications', 'push_notifications',
            'last_login_ip', 'login_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['last_login_ip', 'login_count', 'created_at', 'updated_at']


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration."""
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = [
            'username', 'email', 'password', 'password_confirm',
            'first_name', 'last_name', 'phone', 'timezone', 'language'
        ]
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Passwords don't match.")
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        user = User.objects.create_user(**validated_data)
        
        # Create user profile
        UserProfile.objects.create(user=user)
        
        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating user information."""
    profile = UserProfileSerializer()
    
    class Meta:
        model = User
        fields = [
            'email', 'first_name', 'last_name', 'phone', 'bio',
            'timezone', 'language', 'profile'
        ]
        read_only_fields = ['email']
    
    def update(self, instance, validated_data):
        profile_data = validated_data.pop('profile', {})
        
        # Update user fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update profile fields
        if profile_data:
            profile = instance.profile
            for attr, value in profile_data.items():
                setattr(profile, attr, value)
            profile.save()
        
        return instance


class PasswordChangeSerializer(serializers.Serializer):
    """Serializer for password change."""
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, validators=[validate_password])
    new_password_confirm = serializers.CharField(write_only=True)
    
    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect.")
        return value
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError("New passwords don't match.")
        return attrs
    
    def save(self, **kwargs):
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Custom JWT token serializer."""
    
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        
        # Add custom claims
        token['username'] = user.username
        token['email'] = user.email
        token['first_name'] = user.first_name
        token['last_name'] = user.last_name
        
        return token
    
    def validate(self, attrs):
        data = super().validate(attrs)
        
        # Add user info to response
        data['user'] = UserSerializer(self.user).data
        
        return data


class APIKeySerializer(serializers.ModelSerializer):
    """Serializer for API keys."""
    
    class Meta:
        model = APIKey
        fields = [
            'id', 'name', 'key', 'is_active', 'permissions',
            'last_used', 'usage_count', 'expires_at',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'key', 'last_used', 'usage_count', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        import secrets
        validated_data['key'] = secrets.token_urlsafe(32)
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class APIKeyCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating API keys."""
    
    class Meta:
        model = APIKey
        fields = ['name', 'permissions', 'expires_at']
    
    def create(self, validated_data):
        import secrets
        validated_data['key'] = secrets.token_urlsafe(32)
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)