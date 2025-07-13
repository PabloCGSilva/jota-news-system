"""
Models for webhook app.
"""
from django.db import models
from django.utils import timezone
import uuid
import json


class WebhookSource(models.Model):
    """
    Model to track webhook sources and their configurations.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    endpoint_url = models.URLField(help_text="The URL where this webhook is accessible")
    secret_key = models.CharField(max_length=255, help_text="Secret key for webhook verification")
    is_active = models.BooleanField(default=True)
    
    # Configuration
    expected_content_type = models.CharField(max_length=50, default='application/json')
    requires_authentication = models.BooleanField(default=True)
    rate_limit_per_minute = models.IntegerField(default=100)
    
    # Statistics
    total_requests = models.BigIntegerField(default=0)
    successful_requests = models.BigIntegerField(default=0)
    failed_requests = models.BigIntegerField(default=0)
    last_request_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'webhook_source'
        verbose_name = 'Webhook Source'
        verbose_name_plural = 'Webhook Sources'
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def increment_total_requests(self):
        """Increment total requests counter."""
        self.total_requests += 1
        self.last_request_at = timezone.now()
        self.save(update_fields=['total_requests', 'last_request_at'])
    
    def increment_successful_requests(self):
        """Increment successful requests counter."""
        self.successful_requests += 1
        self.save(update_fields=['successful_requests'])
    
    def increment_failed_requests(self):
        """Increment failed requests counter."""
        self.failed_requests += 1
        self.save(update_fields=['failed_requests'])
    
    @property
    def success_rate(self):
        """Calculate success rate percentage."""
        if self.total_requests == 0:
            return 0
        return round((self.successful_requests / self.total_requests) * 100, 2)


class WebhookLog(models.Model):
    """
    Model to log webhook requests for debugging and monitoring.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('invalid', 'Invalid'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source = models.ForeignKey(
        WebhookSource,
        on_delete=models.CASCADE,
        related_name='logs'
    )
    
    # Request details
    method = models.CharField(max_length=10)
    path = models.CharField(max_length=255)
    headers = models.JSONField(default=dict)
    query_params = models.JSONField(default=dict)
    body = models.TextField()
    
    # Response details
    status_code = models.IntegerField(null=True, blank=True)
    response_data = models.JSONField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    
    # Processing details
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    processing_time = models.FloatField(null=True, blank=True)  # in seconds
    created_news_id = models.UUIDField(null=True, blank=True)
    
    # Metadata
    user_agent = models.CharField(max_length=255, blank=True)
    remote_ip = models.GenericIPAddressField()
    correlation_id = models.CharField(max_length=255, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'webhook_log'
        verbose_name = 'Webhook Log'
        verbose_name_plural = 'Webhook Logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['source', '-created_at']),
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['remote_ip', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.source.name} - {self.method} - {self.status}"
    
    def set_success(self, news_id=None, response_data=None):
        """Mark webhook log as successful."""
        self.status = 'success'
        self.status_code = 200
        self.created_news_id = news_id
        self.response_data = response_data or {}
        self.save(update_fields=['status', 'status_code', 'created_news_id', 'response_data'])
    
    def set_failed(self, error_message, status_code=400):
        """Mark webhook log as failed."""
        self.status = 'failed'
        self.status_code = status_code
        self.error_message = error_message
        self.save(update_fields=['status', 'status_code', 'error_message'])
    
    def set_invalid(self, error_message):
        """Mark webhook log as invalid."""
        self.status = 'invalid'
        self.status_code = 400
        self.error_message = error_message
        self.save(update_fields=['status', 'status_code', 'error_message'])


class WebhookRetry(models.Model):
    """
    Model to track webhook retry attempts.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    webhook_log = models.ForeignKey(
        WebhookLog,
        on_delete=models.CASCADE,
        related_name='retries'
    )
    
    attempt_number = models.IntegerField()
    error_message = models.TextField()
    next_retry_at = models.DateTimeField()
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'webhook_retry'
        verbose_name = 'Webhook Retry'
        verbose_name_plural = 'Webhook Retries'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Retry {self.attempt_number} for {self.webhook_log}"


class WebhookStatistic(models.Model):
    """
    Daily webhook statistics.
    """
    date = models.DateField()
    source = models.ForeignKey(WebhookSource, on_delete=models.CASCADE)
    
    total_requests = models.IntegerField(default=0)
    successful_requests = models.IntegerField(default=0)
    failed_requests = models.IntegerField(default=0)
    invalid_requests = models.IntegerField(default=0)
    
    avg_processing_time = models.FloatField(default=0.0)
    news_created = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'webhook_statistic'
        verbose_name = 'Webhook Statistic'
        verbose_name_plural = 'Webhook Statistics'
        unique_together = ['date', 'source']
        ordering = ['-date']
    
    def __str__(self):
        return f"{self.source.name} - {self.date}"
    
    @property
    def success_rate(self):
        """Calculate success rate percentage."""
        if self.total_requests == 0:
            return 0
        return round((self.successful_requests / self.total_requests) * 100, 2)