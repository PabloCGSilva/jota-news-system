"""
Serializers for webhook app.
"""
from rest_framework import serializers
from django.utils import timezone
from .models import WebhookSource, WebhookLog, WebhookRetry, WebhookStatistic


class WebhookSourceSerializer(serializers.ModelSerializer):
    """Webhook source serializer."""
    
    class Meta:
        model = WebhookSource
        fields = [
            'id', 'name', 'description', 'endpoint_url', 'is_active',
            'expected_content_type', 'requires_authentication', 'rate_limit_per_minute',
            'total_requests', 'successful_requests', 'failed_requests',
            'success_rate', 'last_request_at', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'total_requests', 'successful_requests', 'failed_requests',
            'success_rate', 'last_request_at', 'created_at', 'updated_at'
        ]
        extra_kwargs = {
            'secret_key': {'write_only': True}
        }


class WebhookLogSerializer(serializers.ModelSerializer):
    """Webhook log serializer."""
    source_name = serializers.CharField(source='source.name', read_only=True)
    
    class Meta:
        model = WebhookLog
        fields = [
            'id', 'source', 'source_name', 'method', 'path', 'headers',
            'query_params', 'body', 'status_code', 'response_data',
            'error_message', 'status', 'processing_time', 'created_news_id',
            'user_agent', 'remote_ip', 'correlation_id', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class WebhookRetrySerializer(serializers.ModelSerializer):
    """Webhook retry serializer."""
    
    class Meta:
        model = WebhookRetry
        fields = [
            'id', 'webhook_log', 'attempt_number', 'error_message',
            'next_retry_at', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class WebhookStatisticSerializer(serializers.ModelSerializer):
    """Webhook statistic serializer."""
    source_name = serializers.CharField(source='source.name', read_only=True)
    
    class Meta:
        model = WebhookStatistic
        fields = [
            'id', 'date', 'source', 'source_name', 'total_requests',
            'successful_requests', 'failed_requests', 'invalid_requests',
            'success_rate', 'avg_processing_time', 'news_created',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class NewsWebhookSerializer(serializers.Serializer):
    """
    Serializer for incoming news webhook data.
    This is the expected format for news webhooks.
    """
    title = serializers.CharField(max_length=200)
    content = serializers.CharField(max_length=10000)
    summary = serializers.CharField(max_length=500, required=False, allow_blank=True)
    
    source = serializers.CharField(max_length=200)
    source_url = serializers.URLField(required=False, allow_blank=True)
    author = serializers.CharField(max_length=200, required=False, allow_blank=True)
    
    published_at = serializers.DateTimeField(required=False)
    external_id = serializers.CharField(max_length=200, required=False, allow_blank=True)
    
    # Optional category/classification hints
    category_hint = serializers.CharField(max_length=100, required=False, allow_blank=True)
    subcategory_hint = serializers.CharField(max_length=100, required=False, allow_blank=True)
    tags = serializers.ListField(
        child=serializers.CharField(max_length=50),
        required=False,
        allow_empty=True
    )
    
    # Priority/urgency indicators
    is_urgent = serializers.BooleanField(default=False)
    priority = serializers.ChoiceField(
        choices=['low', 'medium', 'high', 'urgent'],
        default='medium',
        required=False
    )
    
    # Metadata
    metadata = serializers.JSONField(required=False, default=dict)
    
    def validate_published_at(self, value):
        """Validate published_at is not in the future."""
        if value and value > timezone.now():
            raise serializers.ValidationError("Published date cannot be in the future")
        return value
    
    def validate_external_id(self, value):
        """Validate external_id is unique if provided."""
        if value:
            from apps.news.models import News
            if News.objects.filter(external_id=value).exists():
                raise serializers.ValidationError("News with this external ID already exists")
        return value
    
    def validate_title(self, value):
        """Validate title is not empty and has reasonable length."""
        if not value.strip():
            raise serializers.ValidationError("Title cannot be empty")
        if len(value.strip()) < 10:
            raise serializers.ValidationError("Title must be at least 10 characters long")
        return value.strip()
    
    def validate_content(self, value):
        """Validate content is not empty."""
        if not value.strip():
            raise serializers.ValidationError("Content cannot be empty")
        if len(value.strip()) < 50:
            raise serializers.ValidationError("Content must be at least 50 characters long")
        return value.strip()


# WhatsApp webhook serializer removed - external META Business API dependency not needed


class WebhookTestSerializer(serializers.Serializer):
    """
    Serializer for testing webhook endpoints.
    """
    source_id = serializers.UUIDField()
    test_data = serializers.JSONField()
    
    def validate_source_id(self, value):
        """Validate source exists."""
        try:
            WebhookSource.objects.get(id=value)
        except WebhookSource.DoesNotExist:
            raise serializers.ValidationError("Webhook source not found")
        return value