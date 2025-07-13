"""
Serializers for notifications app.
"""
from rest_framework import serializers
from django.contrib.auth.models import User
from django.utils import timezone
from .models import (
    NotificationChannel, NotificationSubscription, NotificationTemplate,
    Notification, NotificationStatistic
)


class NotificationChannelSerializer(serializers.ModelSerializer):
    """Notification channel serializer."""
    
    class Meta:
        model = NotificationChannel
        fields = [
            'id', 'name', 'channel_type', 'description', 'config',
            'is_active', 'is_default', 'rate_limit_per_minute', 'rate_limit_per_hour',
            'total_sent', 'total_delivered', 'total_failed', 'delivery_rate',
            'last_used', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'total_sent', 'total_delivered', 'total_failed', 'delivery_rate',
            'last_used', 'created_at', 'updated_at'
        ]
        extra_kwargs = {
            'config': {'write_only': True}  # Hide sensitive config data
        }


class NotificationSubscriptionSerializer(serializers.ModelSerializer):
    """Notification subscription serializer."""
    user_name = serializers.CharField(source='user.username', read_only=True)
    channel_name = serializers.CharField(source='channel.name', read_only=True)
    channel_type = serializers.CharField(source='channel.channel_type', read_only=True)
    category_names = serializers.StringRelatedField(source='categories', many=True, read_only=True)
    
    class Meta:
        model = NotificationSubscription
        fields = [
            'id', 'user', 'user_name', 'channel', 'channel_name', 'channel_type',
            'destination', 'min_priority', 'categories', 'category_names', 'keywords',
            'is_active', 'urgent_only', 'quiet_hours_start', 'quiet_hours_end',
            'notifications_received', 'last_notification', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'notifications_received', 'last_notification', 'created_at', 'updated_at'
        ]
    
    def validate_destination(self, value):
        """Validate destination based on channel type."""
        channel = self.initial_data.get('channel')
        if channel:
            try:
                channel_obj = NotificationChannel.objects.get(id=channel)
                if channel_obj.channel_type == 'whatsapp':
                    # Validate phone number
                    import re
                    if not re.match(r'^\+?[1-9]\d{1,14}$', value):
                        raise serializers.ValidationError("Invalid phone number format")
                elif channel_obj.channel_type == 'email':
                    # Validate email
                    from django.core.validators import validate_email
                    validate_email(value)
                elif channel_obj.channel_type in ['webhook', 'slack']:
                    # Validate URL
                    from django.core.validators import URLValidator
                    validate_url = URLValidator()
                    validate_url(value)
            except NotificationChannel.DoesNotExist:
                pass
        
        return value


class NotificationTemplateSerializer(serializers.ModelSerializer):
    """Notification template serializer."""
    channel_name = serializers.CharField(source='channel.name', read_only=True)
    
    class Meta:
        model = NotificationTemplate
        fields = [
            'id', 'name', 'template_type', 'channel', 'channel_name',
            'subject', 'body_template', 'is_active', 'is_default', 'max_length',
            'times_used', 'last_used', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'times_used', 'last_used', 'created_at', 'updated_at'
        ]


class NotificationSerializer(serializers.ModelSerializer):
    """Notification serializer."""
    subscription_destination = serializers.CharField(source='subscription.destination', read_only=True)
    channel_name = serializers.CharField(source='subscription.channel.name', read_only=True)
    user_name = serializers.CharField(source='subscription.user.username', read_only=True)
    news_title = serializers.CharField(source='news.title', read_only=True)
    template_name = serializers.CharField(source='template.name', read_only=True)
    
    class Meta:
        model = Notification
        fields = [
            'id', 'subscription', 'subscription_destination', 'channel_name', 'user_name',
            'news', 'news_title', 'template', 'template_name', 'subject', 'message',
            'priority', 'status', 'scheduled_for', 'sent_at', 'delivered_at',
            'external_id', 'response_data', 'error_message', 'retry_count',
            'max_retries', 'metadata', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'sent_at', 'delivered_at', 'external_id', 'response_data',
            'error_message', 'retry_count', 'created_at', 'updated_at'
        ]


class NotificationStatisticSerializer(serializers.ModelSerializer):
    """Notification statistic serializer."""
    channel_name = serializers.CharField(source='channel.name', read_only=True)
    
    class Meta:
        model = NotificationStatistic
        fields = [
            'id', 'date', 'channel', 'channel_name', 'total_sent', 'total_delivered',
            'total_failed', 'total_cancelled', 'urgent_notifications',
            'high_notifications', 'medium_notifications', 'low_notifications',
            'avg_delivery_time', 'delivery_rate', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class SendNotificationSerializer(serializers.Serializer):
    """Serializer for sending manual notifications."""
    subscription_ids = serializers.ListField(
        child=serializers.UUIDField(),
        min_length=1,
        max_length=100
    )
    subject = serializers.CharField(max_length=255, required=False, allow_blank=True)
    message = serializers.CharField(max_length=2000)
    priority = serializers.ChoiceField(
        choices=['low', 'medium', 'high', 'urgent'],
        default='medium'
    )
    scheduled_for = serializers.DateTimeField(required=False)
    
    def validate_subscription_ids(self, value):
        """Validate subscription IDs exist."""
        existing_ids = NotificationSubscription.objects.filter(
            id__in=value,
            is_active=True
        ).values_list('id', flat=True)
        
        missing_ids = set(value) - set(existing_ids)
        if missing_ids:
            raise serializers.ValidationError(
                f"Subscriptions not found: {', '.join(str(id) for id in missing_ids)}"
            )
        return value
    
    def validate_scheduled_for(self, value):
        """Validate scheduled time is not in the past."""
        if value and value < timezone.now():
            raise serializers.ValidationError("Scheduled time cannot be in the past")
        return value


class BulkSubscriptionSerializer(serializers.Serializer):
    """Serializer for bulk subscription operations."""
    user_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1,
        max_length=100
    )
    channel_id = serializers.UUIDField()
    destinations = serializers.ListField(
        child=serializers.CharField(max_length=255),
        required=False
    )
    min_priority = serializers.ChoiceField(
        choices=['low', 'medium', 'high', 'urgent'],
        default='medium'
    )
    categories = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        allow_empty=True
    )
    
    def validate_user_ids(self, value):
        """Validate user IDs exist."""
        existing_ids = User.objects.filter(id__in=value).values_list('id', flat=True)
        missing_ids = set(value) - set(existing_ids)
        
        if missing_ids:
            raise serializers.ValidationError(
                f"Users not found: {', '.join(str(id) for id in missing_ids)}"
            )
        return value
    
    def validate_channel_id(self, value):
        """Validate channel exists."""
        try:
            NotificationChannel.objects.get(id=value, is_active=True)
        except NotificationChannel.DoesNotExist:
            raise serializers.ValidationError("Channel not found or inactive")
        return value
    
    def validate(self, data):
        """Validate destinations match user count."""
        destinations = data.get('destinations', [])
        user_ids = data.get('user_ids', [])
        
        if destinations and len(destinations) != len(user_ids):
            raise serializers.ValidationError(
                "Number of destinations must match number of users"
            )
        
        return data


class NotificationStatsSerializer(serializers.Serializer):
    """Serializer for notification statistics query."""
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)
    channel_id = serializers.UUIDField(required=False)
    
    def validate(self, data):
        """Validate date range."""
        if data.get('date_from') and data.get('date_to'):
            if data['date_from'] > data['date_to']:
                raise serializers.ValidationError("date_from must be before date_to")
        return data


class TestNotificationSerializer(serializers.Serializer):
    """Serializer for testing notifications."""
    channel_id = serializers.UUIDField()
    destination = serializers.CharField(max_length=255)
    subject = serializers.CharField(max_length=255, required=False, allow_blank=True)
    message = serializers.CharField(max_length=1000)
    
    def validate_channel_id(self, value):
        """Validate channel exists."""
        try:
            NotificationChannel.objects.get(id=value, is_active=True)
        except NotificationChannel.DoesNotExist:
            raise serializers.ValidationError("Channel not found or inactive")
        return value


class TemplateTestSerializer(serializers.Serializer):
    """Serializer for testing templates."""
    template_id = serializers.UUIDField()
    context = serializers.JSONField()
    
    def validate_template_id(self, value):
        """Validate template exists."""
        try:
            NotificationTemplate.objects.get(id=value, is_active=True)
        except NotificationTemplate.DoesNotExist:
            raise serializers.ValidationError("Template not found or inactive")
        return value