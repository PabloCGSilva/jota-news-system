"""
Authentication admin for JOTA News System.
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import User, UserProfile, APIKey


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin for User model."""
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'email', 'phone', 'bio')}),
        (_('Preferences'), {'fields': ('timezone', 'language')}),
        (_('Permissions'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2'),
        }),
    )
    
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'is_active', 'created_at')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups', 'created_at')
    search_fields = ('username', 'first_name', 'last_name', 'email')
    ordering = ('-created_at',)
    filter_horizontal = ('groups', 'user_permissions')


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """Admin for UserProfile model."""
    
    list_display = ('user', 'organization', 'position', 'email_notifications', 'sms_notifications', 'created_at')
    list_filter = ('email_notifications', 'sms_notifications', 'push_notifications', 'created_at')
    search_fields = ('user__username', 'user__email', 'organization', 'position')
    ordering = ('-created_at',)
    
    fieldsets = (
        (_('User'), {'fields': ('user',)}),
        (_('Professional Info'), {'fields': ('organization', 'position', 'department')}),
        (_('Notification Preferences'), {
            'fields': ('email_notifications', 'sms_notifications', 'push_notifications')
        }),
        (_('Activity'), {'fields': ('last_login_ip', 'login_count')}),
    )
    
    readonly_fields = ('last_login_ip', 'login_count')


@admin.register(APIKey)
class APIKeyAdmin(admin.ModelAdmin):
    """Admin for APIKey model."""
    
    list_display = ('name', 'user', 'is_active', 'usage_count', 'last_used', 'expires_at', 'created_at')
    list_filter = ('is_active', 'created_at', 'expires_at')
    search_fields = ('name', 'user__username', 'user__email')
    ordering = ('-created_at',)
    
    fieldsets = (
        (_('Basic Info'), {'fields': ('name', 'user', 'is_active')}),
        (_('Key'), {'fields': ('key',)}),
        (_('Permissions'), {'fields': ('permissions',)}),
        (_('Usage'), {'fields': ('usage_count', 'last_used')}),
        (_('Expiration'), {'fields': ('expires_at',)}),
    )
    
    readonly_fields = ('key', 'usage_count', 'last_used')
    
    def save_model(self, request, obj, form, change):
        if not change:  # Creating new API key
            import secrets
            obj.key = secrets.token_urlsafe(32)
        super().save_model(request, obj, form, change)